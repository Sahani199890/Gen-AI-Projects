"""Central settings: load .env once, import values from here everywhere."""
import os
from dotenv import load_dotenv

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "rag-multimodal")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
VISION_MODEL = os.getenv("VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
STT_MODEL = os.getenv("STT_MODEL", "whisper-large-v3-turbo")

EMBED_MODEL = os.getenv("EMBED_MODEL", "multilingual-e5-large")
EMBED_DIM = 1024          # must equal the Pinecone index dimension
DOCS_NAMESPACE = "docs"
MEMORY_NAMESPACE = "memory"
DB_PATH = "app.db"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
TOP_K = 5
