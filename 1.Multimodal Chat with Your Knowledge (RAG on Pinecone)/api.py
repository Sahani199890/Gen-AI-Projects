import shutil
import sys
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from ingest.pipeline import chain_for_pdf_chunk
# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
INGEST_DIR = PROJECT_ROOT / "ingest"
if str(INGEST_DIR) not in sys.path:
    sys.path.insert(0, str(INGEST_DIR))

from db import upsert_records, init_db, get_stats

app = FastAPI(
    title="Multimodal RAG API",
    description="API for ingesting PDF documents and querying Pinecone vector DB",
    version="1.0.0"
)

# Optional: enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to save incoming uploaded files
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.on_event("startup")
def startup_event():
    """Ensure the Pinecone index is created and ready on startup."""
    try:
        init_db()
        print("Pinecone database initialized successfully.")
    except Exception as e:
        print(f"Warning: Could not initialize Pinecone index at startup: {e}")


@app.post("/ingest/pdf", status_code=status.HTTP_201_CREATED)
async def ingest_pdf(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Receives a PDF in the request body, extracts text, chunks it,

    generates embeddings, and stores the records into Pinecone.
    """
    # 1. Validate file extension
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF files are supported."
        )

    saved_file_path = UPLOAD_DIR / file.filename

    try:
        # 2. Save incoming file stream to disk
        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. Load pages using PyMuPDFLoader
        records=chain_for_pdf_chunk(saved_file_path) 

        # 6. Embed and store into Pinecone
        total_upserted = upsert_records(records)

        return {
            "status": "success",
            "message": f"Successfully ingested {file.filename} into Pinecone",
            "filename": file.filename,
            "vectors_stored": total_upserted
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while ingesting the document: {str(e)}"
        )
    finally:
        await file.close()


@app.get("/stats")
def get_index_statistics() -> Dict[str, Any]:
    """Get the current Pinecone index statistics (vector count, namespaces)."""
    try:
        return get_stats()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
