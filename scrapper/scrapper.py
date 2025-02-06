import requests
from bs4 import BeautifulSoup
import json
import numpy as np
import faiss
import os
import time
import shutil
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage, Settings
from llama_index.core.schema import Document
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core.base.embeddings.base import BaseEmbedding
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    CLOUDFLARE_API_URL = "https://api.cloudflare.com/client/v4/accounts/bf52f6782290abdecd497dbd48c23ef3/ai/run/@cf/baai/bge-large-en-v1.5"
    CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY")
    FAISS_INDEX_FILE = "faiss_index.bin"
    STORAGE_DIR = "storage/"
    CHUNK_SIZE = 500
    EMBEDDING_DIMENSION = 1024
    SUPPORTED_FILE_TYPES = ('.txt', '.md', '.html')
    DEFAULT_URL = "https://example.com"

class CloudflareEmbedding(BaseEmbedding):
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {Config.CLOUDFLARE_API_KEY}",
            "Content-Type": "application/json"
        })

    def _get_text_embedding(self, text: str) -> list:
        print(f"Getting embedding for text: {text}")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self._session.post(
                    Config.CLOUDFLARE_API_URL,
                    data=json.dumps({"text": text})
                )
                response.raise_for_status()
                result = response.json()
                
                if "result" in result and "data" in result["result"]:
                    return result["result"]["data"][0]
                raise ValueError(f"Unexpected API response structure: {result}")
            
            except (requests.RequestException, ValueError) as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to get embedding after {max_retries} attempts: {str(e)}")
                print(f"Retry {attempt + 1}/{max_retries} after error: {str(e)}")
                time.sleep(2 ** attempt)

    def _get_query_embedding(self, query: str) -> list:
        return self._get_text_embedding(query)

    async def _aget_query_embedding(self, query: str) -> list:
        return self._get_text_embedding(query)

class DocumentProcessor:
    @staticmethod
    def scrape_website(url: str) -> str:
        """Fetch and parse website content."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            # Get text from paragraphs, headers, and other relevant tags
            text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'article', 'section'])
            text = ' '.join([elem.get_text(strip=True) for elem in text_elements if elem.get_text(strip=True)])
            return text
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return ""

    @staticmethod
    def read_file(file_path: Union[str, Path]) -> str:
        """Read content from various file types."""
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_path.suffix not in Config.SUPPORTED_FILE_TYPES:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        if file_path.suffix == '.html':
            with open(file_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
                return ' '.join([p.get_text(strip=True) for p in soup.find_all('p')])
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def chunk_text(text: str, chunk_size: int = Config.CHUNK_SIZE) -> List[str]:
        """Split text into chunks more intelligently."""
        if not text.strip():
            return []
            
        sentences = text.replace('\n', ' ').split('. ')
        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence_size = len(sentence)
            if current_size + sentence_size > chunk_size and current_chunk:
                chunks.append('. '.join(current_chunk) + '.')
                current_chunk = []
                current_size = 0
            
            current_chunk.append(sentence)
            current_size += sentence_size

        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
        
        return chunks

class VectorStoreManager:
    def __init__(self):
        self.embedding_model = CloudflareEmbedding()
        Settings.embed_model = self.embedding_model
        Settings.llm = None  # Disable OpenAI

    def create_or_load_store(self, documents: Optional[List[Document]] = None) -> VectorStoreIndex:
        """Create new store or load existing one."""
        if self._check_existing_store():
            return self._load_existing_store()
        
        if documents is None:
            # If no documents provided and no existing store, scrape default website
            print("No local files or existing store found. Scraping example.com...")
            processor = DocumentProcessor()
            content = processor.scrape_website(Config.DEFAULT_URL)
            chunks = processor.chunk_text(content)
            documents = [Document(text=chunk) for chunk in chunks if chunk.strip()]
        
        return self._create_new_store(documents)

    def _check_existing_store(self) -> bool:
        """Check if valid store exists."""
        return (Path(Config.FAISS_INDEX_FILE).exists() and 
                Path(Config.STORAGE_DIR).exists())

    def _load_existing_store(self) -> VectorStoreIndex:
        """Load existing vector store."""
        try:
            faiss_index = faiss.read_index(Config.FAISS_INDEX_FILE)
            vector_store = FaissVectorStore(faiss_index)
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                persist_dir=Config.STORAGE_DIR
            )
            return load_index_from_storage(storage_context)
        except Exception as e:
            print(f"Error loading existing store: {e}")
            self._cleanup_storage()
            return None

    def _create_new_store(self, documents: List[Document]) -> VectorStoreIndex:
        """Create new vector store."""
        if not documents:
            raise ValueError("No documents provided to create store")
            
        self._cleanup_storage()
        
        faiss_index = faiss.IndexFlatL2(Config.EMBEDDING_DIMENSION)
        vector_store = FaissVectorStore(faiss_index)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context
        )
        
        # Save both FAISS and LlamaIndex storage
        faiss.write_index(faiss_index, Config.FAISS_INDEX_FILE)
        index.storage_context.persist(persist_dir=Config.STORAGE_DIR)
        
        return index

    def _cleanup_storage(self):
        """Clean up existing storage."""
        shutil.rmtree(Config.STORAGE_DIR, ignore_errors=True)
        if os.path.exists(Config.FAISS_INDEX_FILE):
            os.remove(Config.FAISS_INDEX_FILE)
        
        # create a new directory for the website
        if not os.path.exists(Config.STORAGE_DIR):
            os.makedirs(Config.STORAGE_DIR)

class SearchEngine:
    def __init__(self, index: VectorStoreIndex):
        self.index = index
        self.query_engine = index.as_query_engine(llm=None)

    def search(self, query: str, k: int = 3) -> List[str]:
        """Search for similar content."""
        try:
            response = self.query_engine.query(query)
            if hasattr(response, "response"):
                return [response.response]
            return response if isinstance(response, list) else [str(response)]
        except Exception as e:
            print(f"Search error: {e}")
            return []

class EmbeddingService:
    def scrape_website(self, id,url):
        # if websites directory does not exist, create it
            
        Config.STORAGE_DIR = f"scrapper/websites/{id}/"
        Config.DEFAULT_URL = url
        Config.FAISS_INDEX_FILE = f"scrapper/websites/{id}/faiss_index.bin"
        
        vector_store_manager = VectorStoreManager()
        index = vector_store_manager.create_or_load_store()
        return True

    def query(self, id,url,query):
        Config.STORAGE_DIR = f"scrapper/websites/{id}/"
        Config.DEFAULT_URL = url
        Config.FAISS_INDEX_FILE = f"scrapper/websites/{id}/faiss_index.bin"
        
        processor = DocumentProcessor()
        vector_store_manager = VectorStoreManager()
        docs_dir = Path("documents")
        if docs_dir.exists():
            # Process all supported files in the documents directory
            documents = []
            for file_path in docs_dir.glob("*"):
                if file_path.suffix in Config.SUPPORTED_FILE_TYPES:
                    try:
                        content = processor.read_file(file_path)
                        chunks = processor.chunk_text(content)
                        documents.extend([Document(text=chunk) for chunk in chunks])
                        print(f"Processed: {file_path}")
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
            
            if documents:
                index = vector_store_manager.create_or_load_store(documents)
            else:
                index = vector_store_manager.create_or_load_store()
        else:
            index = vector_store_manager.create_or_load_store()

        if not index:
            print("Failed to initialize index. Exiting...")
            return

        # Initialize search engine
        search_engine = SearchEngine(index)
        result = search_engine.search(query)
        return result

