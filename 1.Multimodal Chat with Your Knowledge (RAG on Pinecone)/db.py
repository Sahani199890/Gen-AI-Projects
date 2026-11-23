"""Pinecone Database Interface for Multimodal RAG.
Stores all document chunks, extracted text, and metadata directly in Pinecone (no SQLite required).
"""
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from config import (
    PINECONE_API_KEY,
    PINECONE_INDEX,
    EMBED_MODEL,
    EMBED_DIM,
    DOCS_NAMESPACE,
    MEMORY_NAMESPACE,
)

_client: Optional[Pinecone] = None
_index = None


def get_pinecone_client() -> Pinecone:
    """Returns a singleton instance of the Pinecone client."""
    global _client
    if _client is None:
        if not PINECONE_API_KEY:
            raise ValueError(
                "PINECONE_API_KEY is not set. Please add it to your .env file."
            )
        _client = Pinecone(api_key=PINECONE_API_KEY)
    return _client


def init_db():
    """Initializes and ensures the Pinecone index exists with matching dimension and metric."""
    global _index
    pc = get_pinecone_client()

    if not pc.has_index(PINECONE_INDEX):
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=EMBED_DIM,  # 1024 for multilingual-e5-large
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    _index = pc.Index(PINECONE_INDEX)
    return _index


def get_index():
    """Returns the Pinecone Index instance (initializing if needed)."""
    global _index
    if _index is None:
        return init_db()
    return _index


def embed_texts(texts: List[str], input_type: str = "passage") -> List[List[float]]:
    """
    Generates embeddings using Pinecone's Inference API.
    Use input_type='passage' for documents/chunks, and 'query' for search questions.
    """
    pc = get_pinecone_client()
    response = pc.inference.embed(
        model=EMBED_MODEL,
        inputs=texts,
        parameters={"input_type": input_type, "truncate": "END"},
    )
    return [item.values for item in response]


def upsert_records(
    records: List[Dict[str, Any]],
    namespace: str = DOCS_NAMESPACE,
    batch_size: int = 50,
) -> int:
    """
    Embeds and stores document records directly in Pinecone.
    Each record contains 'text' and 'metadata'.
    """
    if not records:
        return 0

    index = get_index()
    total_upserted = 0

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        texts = [r["text"] for r in batch]
        embeddings = embed_texts(texts, input_type="passage")

        vectors = []
        for r, emb in zip(batch, embeddings):
            metadata = r.get("metadata", {})
            source = metadata.get("source_file", "unknown")
            chunk_idx = metadata.get("chunk_index", 0)

            # Deterministic vector ID: prevents duplicate vectors on re-upload
            vector_id = f"{source}#{chunk_idx}"

            # Pinecone stores up to 40KB metadata per vector (includes raw text)
            payload_metadata = {
                "text": r["text"],
                **metadata,
            }

            vectors.append({
                "id": vector_id,
                "values": emb,
                "metadata": payload_metadata,
            })

        index.upsert(vectors=vectors, namespace=namespace)
        total_upserted += len(vectors)

    return total_upserted


def query_records(
    query_text: str,
    top_k: int = 5,
    namespace: str = DOCS_NAMESPACE,
    filter_dict: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Embeds a search query and retrieves the top-k most relevant records from Pinecone.
    """
    index = get_index()
    query_vector = embed_texts([query_text], input_type="query")[0]

    response = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace,
        filter=filter_dict,
    )

    results = []
    for match in response.matches:
        results.append({
            "id": match.id,
            "score": match.score,
            "text": match.metadata.get("text", "") if match.metadata else "",
            "metadata": match.metadata or {},
        })
    return results


def delete_document(source_file: str, namespace: str = DOCS_NAMESPACE) -> int:
    """
    Deletes all chunks belonging to a document using its prefix (source_file#).
    """
    index = get_index()
    prefix = f"{source_file}#"
    deleted_count = 0

    # Discover and delete all chunk IDs matching the file prefix
    for page in index.list(prefix=prefix, namespace=namespace):
        ids = [item.id for item in page.vectors]
        if ids:
            index.delete(ids=ids, namespace=namespace)
            deleted_count += len(ids)

    return deleted_count


def list_documents(namespace: str = DOCS_NAMESPACE) -> List[str]:
    """
    Lists unique document source files stored in the given Pinecone namespace.
    """
    index = get_index()
    sources = set()

    for page in index.list(namespace=namespace):
        for item in page.vectors:
            # Vector ID format is {source_file}#{chunk_index}
            if "#" in item.id:
                sources.add(item.id.split("#", 1)[0])
            else:
                sources.add(item.id)

    return sorted(list(sources))


def get_stats() -> Dict[str, Any]:
    """Returns index statistics including total vector counts per namespace."""
    index = get_index()
    return index.describe_index_stats().to_dict()
