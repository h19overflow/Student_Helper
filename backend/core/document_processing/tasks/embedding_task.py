"""
Embedding generation task using Google Gemini.

Generates vector embeddings for document chunks.

Dependencies: langchain_google_genai, hashlib
System role: Third stage of document ingestion pipeline
"""

import hashlib

from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from ..models import Chunk
from dotenv import load_dotenv  
import os
load_dotenv()

class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    pass


class EmbeddingTask:
    """Generate embeddings using Google Gemini."""

    def __init__(
        self,
        api_key: str,
        model: str = "models/gemini-embedding-001",
    ) -> None:
        """
        Initialize embedding task with Google credentials.

        Args:
            api_key: Google API key
            model: Embedding model name

        Raises:
            ValueError: When API key is empty
        """
        self._embeddings = GoogleGenerativeAIEmbeddings(
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            model=model,
        )

    def embed(self, documents: list[Document]) -> list[Chunk]:
        """
        Generate embeddings for documents.

        Args:
            documents: LangChain Documents to embed

        Returns:
            list[Chunk]: Chunks with embeddings

        Raises:
            EmbeddingError: When embedding generation fails
        """
        if not documents:
            return []

        try:
            texts = [doc.page_content for doc in documents]
            embeddings = self._embeddings.embed_documents(texts)

            chunks = []
            for doc, embedding in zip(documents, embeddings):
                chunk_id = self._generate_chunk_id(doc.page_content, doc.metadata)
                chunk = Chunk(
                    id=chunk_id,
                    content=doc.page_content,
                    metadata=doc.metadata,
                    embedding=embedding,
                )
                chunks.append(chunk)

            return chunks
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {e}") from e

    def _generate_chunk_id(self, content: str, metadata: dict) -> str:
        """
        Generate deterministic chunk ID from content and metadata.

        Args:
            content: Chunk text content
            metadata: Chunk metadata

        Returns:
            str: SHA-256 hash of content + source + start_index
        """
        source = metadata.get("source", "")
        start_index = metadata.get("start_index", 0)
        hash_input = f"{content}:{source}:{start_index}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]
