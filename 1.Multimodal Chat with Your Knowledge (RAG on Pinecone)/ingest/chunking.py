"""Phase 3: chunk_text(text, size, overlap) -> list[str]. Prefer paragraph/sentence boundaries."""

from pinecone import Pinecone
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import config

load_dotenv()

class DocType(BaseModel):
    chunk_index:int
    page_content:str
    metadata: Dict[str, Any] = Field(default_factory=dict)

def chunk_content_recursive_text_splitter(raw_documents:List)->List[DocType]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks=text_splitter.split_documents(raw_documents)
    return [
        DocType(
            chunk_index=chunk_index,
            page_content=chunk.page_content,
            metadata=chunk.metadata
        )
         for chunk_index,chunk in enumerate(chunks)
         ]



_pc_client: Optional[Pinecone] = None
def get_pinecone_client() -> Pinecone:
    """Lazily initializes and returns the Pinecone client."""
    global _pc_client
    if _pc_client is None:
        if not config.PINECONE_API_KEY:
            raise ValueError(
                "PINECONE_API_KEY is not set. Please create a .env file with your free Pinecone API key."
            )
        _pc_client = Pinecone(api_key=config.PINECONE_API_KEY)
    return _pc_client



def generate_embeddings(texts: List[str], input_type: str = "passage",batch_size:int=50) -> List[List[float]]:
    """Generates embeddings using Pinecone's free hosted model (multilingual-e5-large).

    Args:
        texts: List of strings to embed.
        input_type: "passage" for document chunks to store, "query" for search queries.

    Returns:
        List of 1024-dimensional embedding vectors.
    """
    if not texts:
        return []

    client = get_pinecone_client()
    all_embeddings:List[List[float]]=[]

    for i in range(0,len(texts),batch_size):
        batch=texts[i:i+batch_size]
        print(f"Embedding batch: {i + 1} to {min(i + batch_size, len(texts))} of {len(texts)}")


        response = client.inference.embed(
            model=config.EMBED_MODEL,
            inputs=batch,
            parameters={"input_type": input_type, "truncate": "END"}
        )
        batch_vectors=[record.values for record in response.data]
        all_embeddings.extend(batch_vectors)
    return all_embeddings 