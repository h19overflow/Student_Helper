"""
S3 Vectors client wrapper.

Provides high-level interface for vector storage and retrieval operations.
Handles connection pooling, retry logic, and metadata filtering.

Dependencies: boto3, backend.configs, backend.core.exceptions
System role: Vector store client for embedding operations
"""

from typing import Any
import uuid

import boto3
from botocore.exceptions import ClientError

from backend.configs import get_settings
from backend.core.exceptions import VectorStoreError
from backend.boundary.vdb.vector_schemas import (
    VectorQuery,
    VectorMetadata,
    VectorSearchResult,
)


class VectorStoreClient:
    """
    S3 Vectors client for vector operations.

    Provides methods for upserting vectors, querying by similarity,
    and deleting vectors with metadata filtering support.
    """

    def __init__(self) -> None:
        """Initialize S3 Vectors client with configuration."""
        settings = get_settings()
        self.config = settings.vector_store

        # Initialize boto3 client for S3 Vectors
        self.client = boto3.client(
            "s3vectors",
            region_name=self.config.aws_region,
        )

    def upsert_vectors(
        self,
        vectors: list[tuple[str, list[float], VectorMetadata]],
    ) -> None:
        """
        Upsert vectors with metadata into S3 Vectors index.

        Uses upsert operation for idempotency (deterministic chunk IDs).

        Args:
            vectors: List of (chunk_id, embedding, metadata) tuples

        Raises:
            VectorStoreError: If upsert operation fails
        """
        try:
            # Prepare vectors for S3 Vectors API
            vector_entries = [
                {
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": metadata.model_dump(mode="json"),
                }
                for chunk_id, embedding, metadata in vectors
            ]

            # Batch upsert to S3 Vectors
            self.client.upsert(
                index_name=self.config.index_name,
                vectors=vector_entries,
            )

        except ClientError as e:
            raise VectorStoreError(
                message="Failed to upsert vectors to S3 Vectors",
                operation="upsert",
                details={"error": str(e), "vector_count": len(vectors)},
            )

    def query_vectors(self, query: VectorQuery) -> list[VectorSearchResult]:
        """
        Query vectors by similarity with optional metadata filtering.

        Args:
            query: Vector query with embedding and filters

        Returns:
            List of search results with metadata and scores

        Raises:
            VectorStoreError: If query operation fails
        """
        try:
            # Build metadata filter
            metadata_filter = {}
            if self.config.enable_session_filtering and query.session_id:
                metadata_filter["session_id"] = str(query.session_id)
            if query.doc_id:
                metadata_filter["doc_id"] = str(query.doc_id)

            # Execute similarity search
            response = self.client.query(
                index_name=self.config.index_name,
                vector=query.embedding,
                top_k=query.top_k,
                filter=metadata_filter if metadata_filter else None,
                include_metadata=True,
            )

            # Parse results
            results = []
            for match in response.get("matches", []):
                if match.get("score", 0.0) >= query.similarity_threshold:
                    results.append(
                        VectorSearchResult(
                            chunk_id=match["id"],
                            content=match["metadata"].get("content", ""),
                            metadata=VectorMetadata(**match["metadata"]),
                            similarity_score=match["score"],
                        )
                    )

            return results

        except ClientError as e:
            raise VectorStoreError(
                message="Failed to query vectors from S3 Vectors",
                operation="query",
                details={"error": str(e), "query": query.model_dump()},
            )

    def delete_vectors(self, chunk_ids: list[str]) -> None:
        """
        Delete vectors by chunk IDs.

        Args:
            chunk_ids: List of chunk identifiers to delete

        Raises:
            VectorStoreError: If delete operation fails
        """
        try:
            self.client.delete(
                index_name=self.config.index_name,
                ids=chunk_ids,
            )

        except ClientError as e:
            raise VectorStoreError(
                message="Failed to delete vectors from S3 Vectors",
                operation="delete",
                details={"error": str(e), "chunk_count": len(chunk_ids)},
            )
