"""
Gemini embedding generator.

Generates embeddings using Google Gemini text-embedding-004.

Dependencies: langchain-google-genai, backend.configs
System role: Embedding generation adapter
"""

from backend.models.chunk import Chunk


class GeminiEmbedder:
    """Gemini embedding generator."""

    def __init__(self) -> None:
        """Initialize Gemini embeddings client."""
        pass

    def embed_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        """
        Generate embeddings for chunks.

        Args:
            chunks: Document chunks

        Returns:
            list[Chunk]: Chunks with embeddings populated
        """
        pass

    def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for query.

        Args:
            query: Query text

        Returns:
            list[float]: Query embedding vector
        """
        pass
