"""
S3 Vectors store for production retrieval.

Provides retrieval interface using Amazon S3 Vectors with session filtering.
Supports session-isolated search and hybrid retrieval preparation.
Uses Google Gemini embeddings (1024-dimensional) for vector generation.

Dependencies: langchain_google_genai, langchain_aws, backend.boundary.vdb.vector_schemas, tenacity
System role: Production vector store (S3 Vectors)
"""

import logging
from typing import Any

from botocore.exceptions import ClientError
from langchain_aws.vectorstores import AmazonS3Vectors
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

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
    Uses Google Gemini embeddings (1024-dimensional) to avoid Bedrock throttling.
    """

    def __init__(
        self,
        vectors_bucket: str = "student-helper-dev-vectors",
        index_name: str = "documents",
        region: str = "ap-southeast-2",
        embedding_region: str = "us-east-1",
        embedding_model_id: str = "text-embedding-004",
    ) -> None:
        """
        Initialize S3 Vectors store with Google Gemini embeddings.

        Args:
            vectors_bucket: S3 Vectors bucket name
            index_name: Index name within the bucket
            region: AWS region for S3 Vectors
            embedding_region: Unused - kept for backwards compatibility
            embedding_model_id: Google embedding model ID (default: text-embedding-004)
        """
        self._vectors_bucket = vectors_bucket
        self._index_name = index_name
        self._region = region

        logger.info(
            f"{__name__}:__init__ - Creating GoogleGenerativeAIEmbeddings with model {embedding_model_id}"
        )

        # Use Google Gemini embeddings (dimensionality passed at embedding time, not init)
        # This avoids Bedrock throttling and matches S3 Vectors 1024-dimensional index
        self._embeddings = GoogleGenerativeAIEmbeddings(model=embedding_model_id)
        logger.info(f"{__name__}:__init__ - GoogleGenerativeAIEmbeddings initialized")

        self._vector_store = AmazonS3Vectors(
            vector_bucket_name=vectors_bucket,
            index_name=index_name,
            embedding=self._embeddings,
            region_name=region,
        )

    @retry(
        retry=retry_if_exception_type((ClientError, Exception)),
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=1, max=30, jitter=5),
        before_sleep=lambda retry_state: logger.warning(
            f"{__name__}:similarity_search - Retry {retry_state.attempt_number}/5 after throttling"
        ),
        reraise=True,
    )
    def _search_with_retry(
        self,
        query: str,
        k: int,
        filter_dict: dict[str, Any] | None,
    ) -> list[tuple]:
        """Execute similarity search with retry on throttling."""
        return self._vector_store.similarity_search_with_score(
            query=query,
            k=k,
            filter=filter_dict,
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

        Includes exponential backoff retry for API transient failures.

        Args:
            query: Search query text
            k: Number of results to return
            session_id: Filter by session ID (for multi-tenant isolation)
            doc_id: Filter by document ID

        Returns:
            list[VectorSearchResult]: Search results with scores and metadata

        Raises:
            ClientError: After max retries exhausted
        """
        filter_dict: dict[str, Any] = {}
        if session_id:
            filter_dict["session_id"] = session_id
        if doc_id:
            filter_dict["doc_id"] = doc_id

        try:
            results = self._search_with_retry(
                query=query,
                k=k,
                filter_dict=filter_dict if filter_dict else None,
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

            logger.info(
                f"{__name__}:similarity_search - Found {len(search_results)} results",
                extra={"session_id": session_id, "k": k},
            )

            return search_results

        except ClientError as e:
            logger.error(f"{__name__}:similarity_search - ClientError after retries: {e}")
            raise
        except Exception as e:
            logger.error(f"{__name__}:similarity_search - {type(e).__name__}: {e}")
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
