"""
S3 Vectors upload task.

Uploads document chunks to Amazon S3 Vectors with metadata for similarity search.
Uses langchain-aws AmazonS3Vectors for LangChain integration.

Dependencies: langchain_aws, langchain_core
System role: Final stage of document ingestion pipeline
"""

import hashlib
import logging

from langchain_aws import BedrockEmbeddings
from langchain_aws.vectorstores import AmazonS3Vectors
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class VectorStoreUploadError(Exception):
    """Raised when vector store upload fails."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class VectorStoreTask:
    """Upload document chunks to S3 Vectors with automatic embedding."""

    def __init__(
        self,
        vectors_bucket: str,
        index_name: str = "documents",
        region: str = "ap-southeast-2",
        embedding_region: str = "us-east-1",
        embedding_model_id: str = "amazon.titan-embed-text-v2:0",
    ) -> None:
        """
        Initialize vector store task with S3 Vectors and Bedrock embeddings.

        Args:
            vectors_bucket: S3 Vectors bucket name
            index_name: Index name within the bucket
            region: AWS region for S3 Vectors
            embedding_region: AWS region for Bedrock embeddings (us-east-1 has higher quota)
            embedding_model_id: Bedrock embedding model ID

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
        self.embedding_region = embedding_region

        self._embeddings = BedrockEmbeddings(
            model_id=embedding_model_id,
            region_name=embedding_region,
        )
        self._vector_store: AmazonS3Vectors | None = None

    def _get_vector_store(self) -> AmazonS3Vectors:
        """
        Get or create S3 Vectors store instance.

        Returns:
            AmazonS3Vectors: Initialized vector store with embeddings
        """
        if self._vector_store is None:
            self._vector_store = AmazonS3Vectors(
                vector_bucket_name=self.vectors_bucket,
                index_name=self.index_name,
                embedding=self._embeddings,
                region_name=self.region,
            )
        return self._vector_store

    def _generate_chunk_id(self, content: str, metadata: dict) -> str:
        """
        Generate deterministic chunk ID from content and metadata.

        Args:
            content: Chunk text content
            metadata: Chunk metadata

        Returns:
            str: SHA-256 hash prefix (16 chars)
        """
        source = metadata.get("source", "")
        start_index = metadata.get("start_index", 0)
        hash_input = f"{content}:{source}:{start_index}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def _sanitize_metadata(
        self,
        metadata: dict,
        document_id: str,
        session_id: str,
        chunk_id: str,
        chunk_index: int,
    ) -> dict:
        """
        Sanitize metadata to fit S3 Vectors 2048 byte limit.

        Keeps only essential filterable fields, discarding PDF-extracted
        metadata (author, title, producer, etc.) that can cause size overflow.

        Args:
            metadata: Original document metadata from PyPDFLoader
            document_id: Document UUID
            session_id: Session UUID
            chunk_id: Generated chunk ID
            chunk_index: Position in document

        Returns:
            dict: Sanitized metadata under 2048 bytes
        """
        return {
            "chunk_id": chunk_id,
            "chunk_index": chunk_index,
            "session_id": session_id,
            "doc_id": document_id,
            "page": metadata.get("page", 0),
        }

    def upload(
        self,
        documents: list[Document],
        document_id: str,
        session_id: str,
    ) -> list[str]:
        """
        Upload documents to S3 Vectors with session isolation.

        Generates embeddings via Bedrock and uploads to S3 Vectors index.
        Each document gets metadata for session filtering during retrieval.

        Args:
            documents: LangChain Documents (chunked text)
            document_id: Document UUID for grouping chunks
            session_id: Session UUID for multi-tenant isolation

        Returns:
            list[str]: List of generated chunk IDs

        Raises:
            ValueError: When documents list is empty
            VectorStoreUploadError: When upload to S3 Vectors fails
        """
        if not documents:
            raise ValueError("No documents to upload")

        chunk_ids = []
        for i, doc in enumerate(documents):
            chunk_id = self._generate_chunk_id(doc.page_content, doc.metadata)
            chunk_ids.append(chunk_id)

            # Replace metadata with sanitized version to avoid S3 Vectors 2048 byte limit
            doc.metadata = self._sanitize_metadata(
                metadata=doc.metadata,
                document_id=document_id,
                session_id=session_id,
                chunk_id=chunk_id,
                chunk_index=i,
            )

        try:
            vector_store = self._get_vector_store()

            ids = vector_store.add_documents(
                documents=documents,
                ids=chunk_ids,
            )

            logger.info(
                "Uploaded documents to S3 Vectors",
                extra={
                    "chunk_count": len(documents),
                    "document_id": document_id,
                    "session_id": session_id,
                    "bucket": self.vectors_bucket,
                    "index": self.index_name,
                },
            )

            return ids

        except Exception as e:
            logger.exception(
                "Failed to upload documents to S3 Vectors",
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
                    "chunk_count": len(documents),
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
