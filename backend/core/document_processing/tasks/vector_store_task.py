"""
S3 Vectors upload task.

Uploads document chunks to Amazon S3 Vectors with metadata for similarity search.
Uses langchain-aws AmazonS3Vectors for LangChain integration.

Dependencies: langchain_aws, langchain_core
System role: Final stage of document ingestion pipeline
"""

import logging
from typing import List

from langchain_aws.vectorstores import AmazonS3Vectors
from langchain_core.documents import Document

from ..models.chunk import Chunk

logger = logging.getLogger(__name__)


class VectorStoreUploadError(Exception):
    """Raised when vector store upload fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class VectorStoreTask:
    """Upload document chunks to S3 Vectors."""

    def __init__(
        self,
        vectors_bucket: str,
        index_name: str = "documents",
        region: str = "ap-southeast-2",
    ) -> None:
        """
        Initialize vector store task.

        Args:
            vectors_bucket: S3 Vectors bucket name
            index_name: Index name within the bucket
            region: AWS region

        Raises:
            ValueError: When vectors_bucket or index_name is empty
        """
        if not vectors_bucket:
            raise ValueError("vectors_bucket cannot be empty")
        if not index_name:
            raise ValueError("index_name cannot be empty")

        self.vectors_bucket = vectors_bucket
        self.index_name = index_name
        self.region = region
        self._vector_store: AmazonS3Vectors | None = None

    def _get_vector_store(self) -> AmazonS3Vectors:
        """
        Get or create S3 Vectors store instance.

        Returns:
            AmazonS3Vectors: Initialized vector store

        Note:
            S3 Vectors handles embeddings internally, so we don't need
            to pass an embedding model. The embeddings are pre-computed
            in the EmbeddingTask.
        """
        if self._vector_store is None:
            self._vector_store = AmazonS3Vectors(
                vector_bucket_name=self.vectors_bucket,
                index_name=self.index_name,
                region_name=self.region,
            )
        return self._vector_store

    def upload(
        self,
        chunks: List[Chunk],
        document_id: str,
        session_id: str,
    ) -> list[str]:
        """
        Upload chunks to S3 Vectors with session isolation.

        Args:
            chunks: List of chunks with pre-computed embeddings
            document_id: Document UUID for grouping chunks
            session_id: Session UUID for multi-tenant isolation

        Returns:
            list[str]: List of uploaded chunk IDs

        Raises:
            ValueError: When chunks list is empty or missing embeddings
            VectorStoreUploadError: When upload to S3 Vectors fails
        """
        if not chunks:
            raise ValueError("No chunks to upload")

        documents = []
        for chunk in chunks:
            if chunk.embedding is None:
                raise ValueError(f"Chunk {chunk.id} missing embedding vector")

            doc = Document(
                page_content=chunk.content,
                metadata={
                    "chunk_id": chunk.id,
                    "session_id": session_id,
                    "doc_id": document_id,
                    "page": chunk.metadata.get("page"),
                    "section": chunk.metadata.get("section"),
                    "source_uri": chunk.metadata.get("source", ""),
                },
            )
            documents.append(doc)

        try:
            vector_store = self._get_vector_store()

            ids = vector_store.add_documents(
                documents=documents,
                ids=[chunk.id for chunk in chunks],
            )

            logger.info(
                "Uploaded chunks to S3 Vectors",
                extra={
                    "chunk_count": len(chunks),
                    "document_id": document_id,
                    "session_id": session_id,
                    "bucket": self.vectors_bucket,
                    "index": self.index_name,
                },
            )

            return ids

        except Exception as e:
            logger.exception(
                "Failed to upload chunks to S3 Vectors",
                extra={
                    "document_id": document_id,
                    "session_id": session_id,
                    "error": str(e),
                },
            )
            raise VectorStoreUploadError(
                message=f"Failed to upload to S3 Vectors: {e}",
                details={
                    "document_id": document_id,
                    "session_id": session_id,
                    "chunk_count": len(chunks),
                },
            ) from e

    def delete_document(self, document_id: str, chunk_ids: list[str]) -> None:
        """
        Delete all chunks for a document.

        Args:
            document_id: Document UUID
            chunk_ids: List of chunk IDs to delete

        Raises:
            VectorStoreUploadError: When deletion fails
        """
        if not chunk_ids:
            return

        try:
            vector_store = self._get_vector_store()
            vector_store.delete(ids=chunk_ids)

            logger.info(
                "Deleted chunks from S3 Vectors",
                extra={
                    "document_id": document_id,
                    "chunk_count": len(chunk_ids),
                },
            )

        except Exception as e:
            logger.exception(
                "Failed to delete chunks from S3 Vectors",
                extra={"document_id": document_id, "error": str(e)},
            )
            raise VectorStoreUploadError(
                message=f"Failed to delete from S3 Vectors: {e}",
                details={"document_id": document_id},
            ) from e
