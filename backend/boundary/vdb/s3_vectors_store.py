"""
S3 Vectors store for production retrieval.

Provides retrieval interface using Amazon S3 Vectors with session filtering.
Supports session-isolated search and hybrid retrieval preparation.

Dependencies: langchain_aws, backend.boundary.vdb.vector_schemas
System role: Production vector store (S3 Vectors)
"""

import logging
from typing import Any

from langchain_aws import BedrockEmbeddings
from langchain_aws.vectorstores import AmazonS3Vectors
from langchain_core.documents import Document

from backend.boundary.vdb.vector_schemas import (
    VectorMetadata,
    VectorSearchResult,
)

logger = logging.getLogger(__name__)


class S3VectorsStore:
    """
    S3 Vectors store for production retrieval.

    Wraps AmazonS3Vectors with session filtering for multi-tenant isolation.
    Supports similarity search, MMR search, and retriever creation.
    """

    def __init__(
        self,
        vectors_bucket: str = "student-helper-dev-vectors",
        index_name: str = "documents",
        region: str = "ap-southeast-2",
        embedding_model_id: str = "amazon.titan-embed-text-v2:0",
    ) -> None:
        """
        Initialize S3 Vectors store with Bedrock embeddings.

        Args:
            vectors_bucket: S3 Vectors bucket name
            index_name: Index name within the bucket
            region: AWS region
            embedding_model_id: Bedrock embedding model ID
        """
        self._vectors_bucket = vectors_bucket
        self._index_name = index_name
        self._region = region

        self._embeddings = BedrockEmbeddings(
            model_id=embedding_model_id,
            region_name=region,
        )

        self._vector_store = AmazonS3Vectors(
            vector_bucket_name=vectors_bucket,
            index_name=index_name,
            embedding=self._embeddings,
            region_name=region,
        )

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        session_id: str | None = None,
        doc_id: str | None = None,
    ) -> list[VectorSearchResult]:
        """
        Search for similar documents with optional filtering.

        Args:
            query: Search query text
            k: Number of results to return
            session_id: Filter by session ID (for multi-tenant isolation)
            doc_id: Filter by document ID

        Returns:
            list[VectorSearchResult]: Search results with scores and metadata
        """
        filter_dict: dict[str, Any] = {}
        if session_id:
            filter_dict["session_id"] = session_id
        if doc_id:
            filter_dict["doc_id"] = doc_id

        try:
            results = self._vector_store.similarity_search_with_score(
                query=query,
                k=k,
                filter=filter_dict if filter_dict else None,
            )

            search_results = []
            for doc, score in results:
                metadata = doc.metadata
                search_results.append(
                    VectorSearchResult(
                        chunk_id=metadata.get("chunk_id", ""),
                        content=doc.page_content,
                        metadata=VectorMetadata(
                            session_id=metadata.get("session_id", ""),
                            doc_id=metadata.get("doc_id", ""),
                            chunk_id=metadata.get("chunk_id", ""),
                            page=metadata.get("page"),
                            section=metadata.get("section"),
                            source_uri=metadata.get("source_uri", ""),
                        ),
                        similarity_score=float(score),
                    )
                )

            logger.debug(
                "Similarity search completed",
                extra={
                    "query_preview": query[:50],
                    "k": k,
                    "result_count": len(search_results),
                    "session_id": session_id,
                },
            )

            return search_results

        except Exception as e:
            logger.exception(
                "Similarity search failed",
                extra={"query_preview": query[:50], "error": str(e)},
            )
            raise

    def max_marginal_relevance_search(
        self,
        query: str,
        k: int = 5,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        session_id: str | None = None,
    ) -> list[VectorSearchResult]:
        """
        MMR search balancing relevance and diversity.

        Args:
            query: Search query text
            k: Number of results to return
            fetch_k: Number of candidates to fetch before MMR
            lambda_mult: Balance factor (0=diversity, 1=relevance)
            session_id: Filter by session ID

        Returns:
            list[VectorSearchResult]: Diverse search results
        """
        filter_dict: dict[str, Any] = {}
        if session_id:
            filter_dict["session_id"] = session_id

        try:
            results = self._vector_store.max_marginal_relevance_search(
                query=query,
                k=k,
                fetch_k=fetch_k,
                lambda_mult=lambda_mult,
                filter=filter_dict if filter_dict else None,
            )

            search_results = []
            for doc in results:
                metadata = doc.metadata
                search_results.append(
                    VectorSearchResult(
                        chunk_id=metadata.get("chunk_id", ""),
                        content=doc.page_content,
                        metadata=VectorMetadata(
                            session_id=metadata.get("session_id", ""),
                            doc_id=metadata.get("doc_id", ""),
                            chunk_id=metadata.get("chunk_id", ""),
                            page=metadata.get("page"),
                            section=metadata.get("section"),
                            source_uri=metadata.get("source_uri", ""),
                        ),
                        similarity_score=1.0,  # MMR doesn't return scores
                    )
                )

            return search_results

        except Exception as e:
            logger.exception(
                "MMR search failed",
                extra={"query_preview": query[:50], "error": str(e)},
            )
            raise

    def as_retriever(
        self,
        search_type: str = "similarity",
        k: int = 5,
        session_id: str | None = None,
        **kwargs: Any,
    ):
        """
        Create a LangChain retriever with session filtering.

        Args:
            search_type: "similarity", "mmr", or "similarity_score_threshold"
            k: Number of results
            session_id: Filter by session ID
            **kwargs: Additional search kwargs

        Returns:
            VectorStoreRetriever: LangChain retriever for chains/agents
        """
        search_kwargs = {"k": k, **kwargs}
        if session_id:
            search_kwargs["filter"] = {"session_id": session_id}

        return self._vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs,
        )

    def delete_by_doc_id(self, doc_id: str, chunk_ids: list[str]) -> None:
        """
        Delete all vectors for a document.

        Args:
            doc_id: Document ID
            chunk_ids: List of chunk IDs to delete
        """
        if not chunk_ids:
            return

        try:
            self._vector_store.delete(ids=chunk_ids)
            logger.info(
                "Deleted document chunks",
                extra={"doc_id": doc_id, "chunk_count": len(chunk_ids)},
            )
        except Exception as e:
            logger.exception(
                "Failed to delete document chunks",
                extra={"doc_id": doc_id, "error": str(e)},
            )
            raise
