import io
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.pdf_loader import chunk_document_pages
from app.services.vector_store import LocalVectorStore, vector_store
from app.services.embeddings import EmbeddingService


client = TestClient(app)


def test_root_endpoint_serves_html():
    """Test that the root endpoint serves the HTML frontend."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Study Buddy" in response.text


def test_health_endpoint():
    """Test that the health endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_documents_endpoint():
    """Test GET /documents returns document list and chunk counts."""
    response = client.get("/documents")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_indexed_chunks" in data
    assert isinstance(data["documents"], list)


def test_upload_non_pdf_file_rejected():
    """Test that uploading a non-PDF file (e.g., .txt) returns 400 Bad Request."""
    file_content = b"This is a plain text file, not a PDF."
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", io.BytesIO(file_content), "text/plain")},
    )
    assert response.status_code == 400
    assert "Only PDF documents (.pdf) are supported" in response.json()["detail"]


def test_upload_empty_pdf_rejected():
    """Test that uploading a 0-byte PDF returns 400 Bad Request."""
    response = client.post(
        "/documents",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_chat_empty_question_rejected():
    """Test that submitting an empty or whitespace-only question returns 400 or 422."""
    response = client.post(
        "/chat",
        json={"question": "   "},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_chat_missing_question_field():
    """Test that omitting the question field returns 422 Unprocessable Entity."""
    response = client.post(
        "/chat",
        json={},
    )
    assert response.status_code == 422


def test_text_chunking_utility():
    """Test that chunk_document_pages correctly splits text while preserving metadata."""
    sample_pages = [
        {
            "page_number": 1,
            "text": "Deadlock is a state in concurrent systems where two or more processes cannot proceed because each is waiting for another.",
        },
        {
            "page_number": 2,
            "text": "The four Coffman conditions for deadlock are: Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait.",
        },
    ]

    chunks = chunk_document_pages(sample_pages, document_name="os_notes.pdf", chunk_size=80, overlap=20)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk["document"] == "os_notes.pdf"
        assert chunk["page"] in [1, 2]
        assert len(chunk["text"]) > 0


def test_vector_store_and_local_embeddings(tmp_path):
    """Test local vector store indexing and cosine similarity retrieval."""
    import asyncio

    async def _run():
        test_store_file = tmp_path / "test_store.json"
        store = LocalVectorStore(storage_path=str(test_store_file))
        emb_service = EmbeddingService()

        # Generate embeddings for test text
        text_a = "Operating systems manage hardware and software resources."
        text_b = "Photosynthesis is the process by which green plants convert light into chemical energy."

        emb_a = await emb_service.get_embedding(text_a)
        emb_b = await emb_service.get_embedding(text_b)

        chunks = [
            {
                "chunk_id": "c1",
                "document": "os.pdf",
                "page": 1,
                "text": text_a,
                "embedding": emb_a,
            },
            {
                "chunk_id": "c2",
                "document": "bio.pdf",
                "page": 5,
                "text": text_b,
                "embedding": emb_b,
            },
        ]

        store.add_chunks(chunks)
        assert store.count() == 2
        assert "os.pdf" in store.list_documents()

        # Query with something related to OS
        query_emb = await emb_service.get_embedding("operating system and hardware")
        results = store.search(query_emb, top_k=1)

        assert len(results) == 1
        assert results[0]["document"] == "os.pdf"

    asyncio.run(_run())


def test_end_to_end_pdf_upload_and_chat():
    """Test full workflow: upload a valid PDF, verify indexing, and query the chat endpoint."""
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n"
        b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"5 0 obj << /Length 73 >> stream\n"
        b"BT\n/F1 12 Tf\n72 712 Td\n"
        b"(Deadlock occurs when four Coffman conditions are met in an OS.) Tj\n"
        b"ET\nendstream\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000010 00000 n \n"
        b"0000000060 00000 n \n"
        b"0000000117 00000 n \n"
        b"0000000224 00000 n \n"
        b"0000000295 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\n"
        b"startxref\n419\n%%EOF\n"
    )

    test_filename = "operating_systems.pdf"
    test_filepath = Path("documents") / test_filename

    try:
        # 1. Upload the PDF
        upload_res = client.post(
            "/documents",
            files={"file": (test_filename, io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert upload_res.status_code == 201
        upload_data = upload_res.json()
        assert upload_data["status"] == "success"
        assert upload_data["filename"] == test_filename
        assert upload_data["pages_parsed"] >= 1
        assert upload_data["chunks_stored"] >= 1

        # 2. Check documents list
        docs_res = client.get("/documents")
        assert docs_res.status_code == 200
        docs_data = docs_res.json()
        assert any(d["filename"] == test_filename for d in docs_data["documents"])

        # 3. Ask a question via /chat
        chat_res = client.post(
            "/chat",
            json={"question": "What conditions cause a deadlock?"},
        )
        assert chat_res.status_code == 200
        chat_data = chat_res.json()
        assert "answer" in chat_data
        assert len(chat_data["sources"]) > 0
        assert chat_data["sources"][0]["document"] == test_filename
    finally:
        # Clean up test artifacts so repository stays clean
        if test_filepath.is_file():
            test_filepath.unlink()
        vector_store.clear()

