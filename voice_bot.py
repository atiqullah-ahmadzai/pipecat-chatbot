import asyncio
import os
import sys
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import Frame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIProcessor
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.google import GoogleLLMService, LLMSearchResponseFrame
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter
from pipecat.services.groq import GroqLLMService
from scrapper.scrapper import EmbeddingService

sys.path.append(str(Path(__file__).parent.parent))
from runner import configure

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")
CONFIG = {}

class QueryProcessor(FrameProcessor):
    def __init__(self, embedding_service, context_aggregator, llm):
        super().__init__()
        self.embedding_service = embedding_service
        self.context_aggregator = context_aggregator
        self.processed_frames = set()
        self.llm = llm
        self.current_text_buffer = []
        self.last_processed_text = None
        self.question_markers = {"?", "!", "."}
        
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if hasattr(frame, "text") and frame.text.strip():
            current_text = frame.text.strip()
            self.current_text_buffer.append(current_text)
            complete_text = " ".join(self.current_text_buffer)
            if (any(complete_text.endswith(marker) for marker in self.question_markers) or 
                "stop speaking" in complete_text.lower()):
                clean_text = complete_text.replace("stop speaking", "").strip()
                if clean_text != self.last_processed_text and clean_text:
                    print(f"Processing complete phrase: {clean_text}")
                    
                    search_results = self.embedding_service.query(
                        CONFIG["website_id"], 
                        CONFIG["website_url"], 
                        clean_text
                    )
                    
                    print(f"QueryProcessor: Retrieved Search Results -> {search_results}")

                    if isinstance(search_results, list):
                        if all(isinstance(item, dict) for item in search_results):
                            retrieved_context = "\n".join([doc.get("content", "") for doc in search_results])
                        elif all(isinstance(item, str) for item in search_results):
                            retrieved_context = "\n".join(search_results)
                        else:
                            retrieved_context = "No relevant context found."
                    else:
                        retrieved_context = "No relevant context found."

                    new_context = OpenAILLMContext([
                        {
                            "role": "system",
                            "content": f"Use the following context to answer questions:\n{retrieved_context}"
                        },
                        {
                            "role": "user",
                            "content": clean_text
                        }
                    ])
                    
                    self.context_aggregator = self.llm.create_context_aggregator(new_context)
                    context_frame = self.context_aggregator.user().get_context_frame()
                    await self.push_frame(context_frame)
                    self.last_processed_text = clean_text
                self.current_text_buffer = []
                
        await self.push_frame(frame)

        
class LLMSearchLoggerProcessor(FrameProcessor):
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMSearchResponseFrame):
            print(f"LLMSearchLoggerProcessor: {frame}")
        await self.push_frame(frame)

async def main():
    
    async with aiohttp.ClientSession() as session:
        (room_url, token) = await configure(session)
        transport = DailyTransport(
            room_url,
            token,
            "Voice Assistant!",
            DailyParams(
                audio_out_enabled=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                vad_audio_passthrough=True,
            ),
        )

        stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))
        tts = CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY"),
            voice_id="79a125e8-cd45-4c13-8a67-188112f4dd22",
            text_filter=MarkdownTextFilter(),
        )

        llm = GroqLLMService(
            api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.1-8b-instant"
        )

        context = OpenAILLMContext(
            [
                {"role": "system", "content": "You are a helpful assistant, only provide information provided in context, if query is not readable or understandable, say you don't know about this query."}
            ],
        )
        
        context_aggregator = llm.create_context_aggregator(context)
        embedding_service = EmbeddingService()
        query_processor = QueryProcessor(embedding_service,context_aggregator,llm)
        
        llm_search_logger = LLMSearchLoggerProcessor()
        rtvi = RTVIProcessor(config=RTVIConfig(config=[]))
        pipeline = Pipeline(
            [
                transport.input(),
                stt,
                rtvi,
                query_processor,
                context_aggregator.user(),
                llm,
                llm_search_logger,
                #tts,
                transport.output(),
                context_aggregator.assistant(),
            ]
        )

        task = PipelineTask(
            pipeline,
            PipelineParams(
                allow_interruptions=True,
                observers=[rtvi.observer()],
            ),
        )

        @rtvi.event_handler("on_client_ready")
        async def on_client_ready(rtvi):
            await rtvi.set_bot_ready()

        @transport.event_handler("on_first_participant_joined")
        async def on_first_participant_joined(transport, participant):
            await task.queue_frames([context_aggregator.user().get_context_frame()])

        @transport.event_handler("on_participant_left")
        async def on_participant_left(transport, participant, reason):
            print(f"Participant left: {participant}")
            await task.cancel()

        runner = PipelineRunner()
        await runner.run(task)

def parse_args():
    args = sys.argv 
    
    CONFIG["room_url"] = args[args.index("-u") + 1] if "-u" in args else None
    CONFIG["token"] = args[args.index("-t") + 1] if "-t" in args else None
    CONFIG["website_url"] = args[args.index("-l") + 1] if "-l" in args else None
    CONFIG["website_id"] = args[args.index("-i") + 1] if "-i" in args else None
    
if __name__ == "__main__":
    parse_args()

    asyncio.run(main())
