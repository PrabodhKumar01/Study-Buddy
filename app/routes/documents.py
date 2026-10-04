"""Document management and upload routes.

Handles uploading study PDFs, storing them in the documents/ directory,
parsing and chunking text, generating embeddings, and indexing them into the vector store.
"""
import os
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel

from app.services.rag import rag_service
from app.services.vector_store import vector_store

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

is_vercel = os.getenv("VERCEL") == "1"
default_docs_dir = "/tmp/documents" if is_vercel else "documents"
DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", default_docs_dir))
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


class DocumentSummary(BaseModel):
    filename: str
    size_bytes: int


class DocumentListResponse(BaseModel):
    total_documents: int
    total_indexed_chunks: int
    documents: list[DocumentSummary]


@router.get("", response_model=DocumentListResponse, summary="List all uploaded study documents")
@router.get("/", include_in_schema=False, response_model=DocumentListResponse)
async def list_documents():
    """Retrieve a list of uploaded documents and current vector store index statistics."""
    files = []
    if DOCUMENTS_DIR.is_dir():
        for item in DOCUMENTS_DIR.iterdir():
            if item.is_file() and item.suffix.lower() == ".pdf":
                files.append({
                    "filename": item.name,
                    "size_bytes": item.stat().st_size,
                })

    return {
        "total_documents": len(files),
        "total_indexed_chunks": vector_store.count(),
        "documents": files,
    }



@router.post("", summary="Upload a study document (PDF)", status_code=status.HTTP_201_CREATED)
@router.post("/", include_in_schema=False, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    """Upload a study PDF file, extract its text, chunk it, embed it, and store in the local vector database.

    Handles:
    - Non-PDF rejection (400 Bad Request)
    - Empty file rejection (400 Bad Request)
    - PDF parsing / password error handling
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file selected. Please select a valid PDF file to upload.",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format: '{file.filename}'. Only PDF documents (.pdf) are supported.",
        )

    # Save destination
    safe_filename = Path(file.filename).name
    save_path = DOCUMENTS_DIR / safe_filename

    try:
        # Save file to documents/ directory
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Check if saved file is empty
        if save_path.stat().st_size == 0:
            if save_path.exists():
                save_path.unlink()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uploaded file '{safe_filename}' is empty (0 bytes).",
            )

        # Ingest and index PDF through RAG pipeline
        result = await rag_service.ingest_pdf(save_path, safe_filename)

        return {
            "status": "success",
            "message": f"Successfully processed and indexed '{safe_filename}'.",
            "filename": safe_filename,
            "pages_parsed": result["pages_parsed"],
            "chunks_stored": result["chunks_stored"],
            "total_indexed_chunks": vector_store.count(),
        }

    except HTTPException:
        raise
    except ValueError as val_err:
        # Clean up corrupted/unreadable uploaded file
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except Exception as exc:
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the PDF: {str(exc)}",
        )
    finally:
        await file.close()
