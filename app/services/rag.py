"""RAG (Retrieval-Augmented Generation) pipeline service.

Orchestrates document ingestion, chunking, embedding generation, local vector storage,
similarity retrieval, and grounded answer synthesis via a local open-weight LLM.
"""
from pathlib import Path
from typing import Dict, Any, List

from app.utils.pdf_loader import load_pdf_text, chunk_document_pages
from app.services.vector_store import vector_store
from app.services.embeddings import embedding_service
from app.services.llm import llm_service


SYSTEM_PROMPT = """You are Study Buddy, a helpful and precise academic study assistant.
Answer the user's question using ONLY the provided Study Materials Context.

Strict Guidelines:
1. Base your answer strictly on the provided context excerpts.
2. If the answer cannot be found in the provided context, state clearly: "I could not find the answer in the uploaded study materials."
3. Do NOT make up facts or extrapolate beyond the provided text.
4. Keep explanations clear, concise, and beginner-friendly.
"""


class RAGService:
    """Orchestrates retrieval-augmented generation for study documents."""

    def __init__(self):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.llm_service = llm_service

    async def ingest_pdf(self, file_path: Path, filename: str) -> Dict[str, Any]:
        """Ingest a PDF file: extract text, chunk it, compute embeddings, and store in vector store.

        Args:
            file_path: Absolute or relative Path to the saved PDF file.
            filename: Original name of the document for citation tracking.

        Returns:
            Dictionary with ingestion statistics (pages, chunks count).
        """
        # 1. Extract text page by page
        pages_data = load_pdf_text(file_path)

        # 2. Chunk text with page and document metadata
        chunks = chunk_document_pages(
            pages_data=pages_data,
            document_name=filename,
            chunk_size=600,
            overlap=100,
        )

        if not chunks:
            raise ValueError(f"No usable text chunks could be created from '{filename}'.")

        # 3. Generate embeddings for each chunk
        chunk_texts = [c["text"] for c in chunks]
        embeddings = await self.embedding_service.get_embeddings_batch(chunk_texts)

        # 4. Attach embeddings to chunks
        for chunk, emb in zip(chunks, embeddings):
            chunk["embedding"] = emb

        # 5. Save to local vector store
        added_count = self.vector_store.add_chunks(chunks)

        return {
            "document": filename,
            "pages_parsed": len(pages_data),
            "chunks_stored": added_count,
        }

    async def answer_query(self, question: str, top_k: int = 4) -> Dict[str, Any]:
        """Perform RAG retrieval and generate a grounded answer to the user's question.

        Args:
            question: The user's study query.
            top_k: Number of relevant text chunks to retrieve.

        Returns:
            Dict containing 'answer' and a list of 'sources'.
        """
        clean_question = question.strip()
        if not clean_question:
            return {
                "answer": "Please provide a valid question.",
                "sources": [],
            }

        # Check if vector store is initialized with documents
        if self.vector_store.count() == 0:
            return {
                "answer": (
                    "No study materials have been uploaded yet. "
                    "Please upload a PDF document before asking questions."
                ),
                "sources": [],
            }

        # 1. Create embedding for user question
        query_embedding = await self.embedding_service.get_embedding(clean_question)

        # 2. Retrieve most relevant document chunks
        matched_chunks = self.vector_store.search(query_embedding, top_k=top_k)

        if not matched_chunks:
            return {
                "answer": "I could not find any relevant information in the uploaded study materials.",
                "sources": [],
            }

        # 3. Construct context string for the prompt
        context_blocks = []
        for i, chunk in enumerate(matched_chunks, start=1):
            block = (
                f"[Source {i}: {chunk['document']}, Page {chunk['page']}]\n"
                f"{chunk['text']}"
            )
            context_blocks.append(block)

        context_str = "\n\n--------------------\n\n".join(context_blocks)

        prompt = (
            f"Study Materials Context:\n{context_str}\n\n"
            f"--------------------\n"
            f"User Question: {clean_question}\n\n"
            f"Answer:"
        )

        # 4. Generate answer using local LLM
        answer = await self.llm_service.generate_response(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
        )

        # 5. Format sources for response (deduplicating document + page references)
        sources: List[Dict[str, Any]] = []
        seen = set()
        for chunk in matched_chunks:
            key = (chunk["document"], chunk["page"])
            if key not in seen:
                seen.add(key)
                # Create a concise snippet
                snippet = chunk["text"]
                if len(snippet) > 160:
                    snippet = snippet[:157] + "..."
                sources.append({
                    "document": chunk["document"],
                    "page": chunk["page"],
                    "snippet": snippet,
                    "relevance_score": chunk.get("similarity_score", 0.0),
                })

        return {
            "answer": answer,
            "sources": sources,
        }


# Singleton instance
rag_service = RAGService()
