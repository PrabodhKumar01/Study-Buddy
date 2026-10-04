"""Simple, beginner-friendly local vector store.

Stores text chunks and their embedding vectors in a local JSON file in data/
and performs cosine similarity search using NumPy without requiring external
cloud vector databases.
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any
import numpy as np


class LocalVectorStore:
    """A lightweight local vector store backed by a JSON file and NumPy cosine similarity."""

    def __init__(self, storage_path: str | None = None):
        if storage_path is None:
            is_vercel = os.getenv("VERCEL") == "1"
            default_path = "/tmp/data/vector_store.json" if is_vercel else "data/vector_store.json"
            storage_path = os.getenv("VECTOR_STORE_PATH", default_path)

        self.storage_path = Path(storage_path)
        # Ensure parent directory exists (e.g. data/)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.records: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Load stored chunks and embeddings from disk if the file exists."""
        if self.storage_path.is_file():
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.records = data
            except Exception as e:
                # If file is empty or corrupted, start with an empty store
                self.records = []

    def _save(self) -> None:
        """Persist current records and embeddings to disk."""
        temp_path = self.storage_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2)
        # Atomic rename on Windows/Linux
        temp_path.replace(self.storage_path)

    def add_chunks(self, chunks_with_embeddings: List[Dict[str, Any]]) -> int:
        """Add new chunks with their computed embedding vectors.

        Each item must contain:
        - 'chunk_id': unique identifier string
        - 'document': source document name
        - 'page': source page number
        - 'text': chunk text content
        - 'embedding': list of float numbers

        Returns:
            Number of newly added chunks.
        """
        # Remove any existing chunks with matching chunk_ids to prevent duplicates
        new_ids = {c["chunk_id"] for c in chunks_with_embeddings}
        self.records = [r for r in self.records if r.get("chunk_id") not in new_ids]

        self.records.extend(chunks_with_embeddings)
        self._save()
        return len(chunks_with_embeddings)

    def search(self, query_embedding: List[float], top_k: int = 4) -> List[Dict[str, Any]]:
        """Search the store for the top-k most similar chunks using cosine similarity.

        Args:
            query_embedding: The vector representation of the user's question.
            top_k: Number of relevant chunks to retrieve.

        Returns:
            List of matching chunk dicts with 'similarity_score', sorted highest first.
        """
        if not self.records or not query_embedding:
            return []

        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        results = []

        for record in self.records:
            emb = record.get("embedding")
            if not emb:
                continue

            doc_vec = np.array(emb, dtype=np.float32)
            doc_norm = np.linalg.norm(doc_vec)

            if doc_norm == 0:
                similarity = 0.0
            else:
                similarity = float(np.dot(query_vec, doc_vec) / (query_norm * doc_norm))

            results.append({
                "chunk_id": record.get("chunk_id"),
                "document": record.get("document"),
                "page": record.get("page"),
                "text": record.get("text"),
                "similarity_score": round(similarity, 4),
            })

        # Sort descending by similarity score
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

    def list_documents(self) -> List[str]:
        """Return a sorted list of unique document names currently stored."""
        docs = {r.get("document") for r in self.records if r.get("document")}
        return sorted(list(docs))

    def count(self) -> int:
        """Return the total number of text chunks currently indexed."""
        return len(self.records)

    def clear(self) -> None:
        """Clear all stored chunks and update disk file."""
        self.records = []
        self._save()


# Singleton instance
vector_store = LocalVectorStore()
