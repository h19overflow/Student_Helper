"""
Embedding generation task using Amazon Bedrock Titan Embeddings v2.

Generates vector embeddings for document chunks (1536 dimensions).

Dependencies: langchain_aws, hashlib
System role: Third stage of document ingestion pipeline
"""

import hashlib

from langchain_core.documents import Document
from langchain_aws import BedrockEmbeddings

from ..models import Chunk


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""

    pass


class EmbeddingTask:
    """Generate embeddings using Amazon Titan Embeddings v2."""

    def __init__(
        self,
        model_id: str = "amazon.titan-embed-text-v2:0",
        region: str = "us-east-1",
    ) -> None:
        """
        Initialize embedding task with Bedrock credentials.

        Args:
            model_id: Bedrock model ID (Titan v2 = 1536 dimensions)
            region: AWS region

        Raises:
            ValueError: When model_id is empty
        """
        if not model_id:
            raise ValueError("model_id cannot be empty")

        # TODO: Configure Bedrock credentials via environment or IAM role
        self._embeddings = BedrockEmbeddings(
            model_id=model_id,
            region_name=region,
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
