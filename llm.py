from dotenv import load_dotenv
import openai
import os

load_dotenv(override=True)
class GroqService:
    def ask_ai(self, vector):

        prompt = ""
        if len(vector) == 0:
            prompt = "No context found, you simply say you don't know"
        else:
            prompt = vector[0]
            
        client = openai.OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1" 
        )
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "You are a helpful assistant, only provide information provided in context, if query is not readable or understandable, say you don't know about this query."},{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content
        

    