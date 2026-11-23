import sys
from pathlib import Path
from typing import List, Dict, Any
from langchain_community.document_loaders import PyMuPDFLoader
from chunking import chunk_content_recursive_text_splitter,generate_embeddings

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_document_chunk(file_path: str | Path) -> List[Dict[str, Any]]:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found at {file_path}")

    loader = PyMuPDFLoader(str(path))
    raw_documents = loader.load()
    return raw_documents


if __name__ == "__main__":
    file_path = PROJECT_ROOT / "data" / "Abhishek-Sahani-Resume.pdf"
    chunks = load_document_chunk(file_path)
    print(f"Loaded {len(chunks)} chunks.")

    splitted_chunks_list= chunk_content_recursive_text_splitter(chunks)

    # Generate embeddings
    embeddings = generate_embeddings([chunk.page_content for chunk in splitted_chunks_list],batch_size=20)
    print(f"Generated {len(embeddings)} embeddings of dimension {len(embeddings[0])}.")
