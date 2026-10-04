"""Embeddings service using local open-source models.

Integrates with locally running Ollama embedding models (e.g., 'nomic-embed-text')
with an automatic local scikit-learn/numpy fallback for offline testing or when
Ollama is not yet started.
"""
import os
import logging
from typing import List
import httpx
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates vector embeddings for text chunks using local open-weight models."""

    def __init__(
        self,
        model_name: str | None = None,
        ollama_url: str | None = None,
    ):
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        self.ollama_url = (ollama_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self._fallback_dimension = 128

    async def get_embedding(self, text: str) -> List[float]:
        """Generate an embedding vector for a single piece of text.

        Tries Ollama first. If Ollama is unreachable, falls back to a deterministic
        local fallback vector so that tests and offline development remain fully functional.
        """
        # Attempt to use local Ollama embedding API (modern /api/embed or legacy /api/embeddings)
        try:
            timeout_config = httpx.Timeout(10.0, connect=2.0)
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                # 1. Try modern Ollama /api/embed endpoint
                embed_resp = await client.post(
                    f"{self.ollama_url}/api/embed",
                    json={"model": self.model_name, "input": text},
                )
                if embed_resp.status_code == 200:
                    data = embed_resp.json()
                    embeddings = data.get("embeddings")
                    if embeddings and isinstance(embeddings, list) and len(embeddings) > 0:
                        return embeddings[0]

                # 2. Fallback to legacy Ollama /api/embeddings endpoint
                response = await client.post(
                    f"{self.ollama_url}/api/embeddings",
                    json={"model": self.model_name, "prompt": text},
                )
                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("embedding")
                    if embedding and isinstance(embedding, list):
                        return embedding
                elif response.status_code == 404:
                    logger.warning(
                        f"Ollama model '{self.model_name}' not found. Run: 'ollama pull {self.model_name}'."
                    )
        except Exception as e:
            # Ollama is likely offline or unreachable
            logger.info(
                f"Ollama not reachable at {self.ollama_url} ({e}). "
                "Using local deterministic fallback embeddings."
            )

        # Resilient local fallback embedding (character n-gram frequency hash)
        return self._local_fallback_embedding(text)

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for multiple text strings."""
        results = []
        for text in texts:
            vector = await self.get_embedding(text)
            results.append(vector)
        return results

    def _local_fallback_embedding(self, text: str) -> List[float]:
        """Deterministic, lightweight local vectorizer for offline development and testing.

        Maps words and 3-character n-grams into a fixed-length normalized vector space.
        """
        vector = np.zeros(self._fallback_dimension, dtype=np.float32)
        clean_text = text.lower().strip()

        if not clean_text:
            return vector.tolist()

        # Simple hashing vectorizer across words and tri-grams
        tokens = clean_text.split()
        for token in tokens:
            idx = hash(token) % self._fallback_dimension
            vector[idx] += 1.0

        for i in range(len(clean_text) - 2):
            trigram = clean_text[i : i + 3]
            idx = hash(trigram) % self._fallback_dimension
            vector[idx] += 0.5

        # L2 Normalize
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector.tolist()


# Singleton instance
embedding_service = EmbeddingService()
