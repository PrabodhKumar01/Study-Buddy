"""PDF loading, text extraction, and text chunking utilities.

Extracts text from PDF documents and splits it into manageable, overlapping
chunks suitable for vector embeddings and RAG retrieval.
"""
from pathlib import Path
from typing import List, Dict, Any
import re
from pypdf import PdfReader


def load_pdf_text(file_path: str | Path) -> List[Dict[str, Any]]:
    """Extract text from each page of a given PDF file.

    Args:
        file_path: Path to the target PDF file.

    Returns:
        List of dictionaries containing page number (1-indexed) and extracted text.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is not a valid PDF or has no extractable text.
    """
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"PDF file not found at: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a PDF file (.pdf), but received: {path.name}")

    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise ValueError(f"Could not parse PDF file '{path.name}': {str(exc)}") from exc

    if reader.is_encrypted:
        try:
            # Attempt to decrypt with empty password for unencrypted/read-only protected PDFs
            reader.decrypt("")
        except Exception:
            raise ValueError(f"PDF file '{path.name}' is password-protected and cannot be read.")

    pages_data = []
    total_pages = len(reader.pages)

    if total_pages == 0:
        raise ValueError(f"PDF file '{path.name}' contains no pages.")

    total_extracted_characters = 0

    for page_idx, page in enumerate(reader.pages):
        raw_text = page.extract_text() or ""
        # Clean extra whitespace while preserving sentence boundaries
        cleaned_text = re.sub(r"[ \t]+", " ", raw_text).strip()
        if cleaned_text:
            total_extracted_characters += len(cleaned_text)
            pages_data.append({
                "page_number": page_idx + 1,
                "text": cleaned_text,
            })

    if total_extracted_characters == 0:
        raise ValueError(
            f"No readable text could be extracted from '{path.name}'. "
            "The PDF might contain scanned images without OCR."
        )

    return pages_data


def chunk_document_pages(
    pages_data: List[Dict[str, Any]],
    document_name: str,
    chunk_size: int = 600,
    overlap: int = 100,
) -> List[Dict[str, Any]]:
    """Split page-level text into smaller overlapping chunks for retrieval.

    Preserves document name, page number, and chunk index for accurate citations.

    Args:
        pages_data: List of page dictionaries with 'page_number' and 'text'.
        document_name: Name of the document (e.g., 'lecture1.pdf').
        chunk_size: Maximum approximate character size per chunk.
        overlap: Character overlap between consecutive chunks.

    Returns:
        List of chunk dicts: {chunk_id, document, page, text}.
    """
    chunks: List[Dict[str, Any]] = []
    global_chunk_idx = 0

    step = max(1, chunk_size - overlap)

    for page in pages_data:
        page_num = page["page_number"]
        page_text = page["text"]

        if len(page_text) <= chunk_size:
            chunks.append({
                "chunk_id": f"{document_name}_p{page_num}_c{global_chunk_idx}",
                "document": document_name,
                "page": page_num,
                "text": page_text,
            })
            global_chunk_idx += 1
            continue

        start = 0
        while start < len(page_text):
            end = start + chunk_size
            chunk_slice = page_text[start:end]

            # If not at the end of the text, try to break at a whitespace or newline for readability
            if end < len(page_text):
                last_space = chunk_slice.rfind(" ")
                if last_space > chunk_size // 2:
                    end = start + last_space
                    chunk_slice = page_text[start:end]

            clean_chunk = chunk_slice.strip()
            if clean_chunk:
                chunks.append({
                    "chunk_id": f"{document_name}_p{page_num}_c{global_chunk_idx}",
                    "document": document_name,
                    "page": page_num,
                    "text": clean_chunk,
                })
                global_chunk_idx += 1

            start = end - overlap if (end - overlap) > start else end

    return chunks
