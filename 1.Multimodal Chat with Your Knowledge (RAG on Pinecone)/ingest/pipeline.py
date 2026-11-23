from pathlib import Path
from typing import List, Dict, Any
from ingest.document_loader import load_document_chunk
from ingest.chunking import chunk_content_recursive_text_splitter

def chain_for_pdf_chunk(file_path: str | Path) -> List[Dict[str, Any]]:
    path=Path(file_path)
    pages=load_document_chunk(file_path)
    chunks= chunk_content_recursive_text_splitter(pages)
    records = [
        {
            "text": chunk.page_content,
            "metadata": {
                **chunk.metadata,
                "source_file": path.name,
                "chunk_index": chunk.chunk_index,
            }
        }
        for chunk in chunks
    ]

    return records