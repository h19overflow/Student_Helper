"""
S3 Vectors store for production retrieval.

Provides retrieval interface using Amazon S3 Vectors with session filtering.
Supports session-isolated search and hybrid retrieval preparation.
Includes exponential backoff retry for Bedrock throttling.
Uses LRU cache for embeddings to reduce API calls.

Dependencies: langchain_aws, backend.boundary.vdb.vector_schemas, tenacity, boto3
System role: Production vector store (S3 Vectors)
"""

import hashlib
import logging
from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from langchain_aws import BedrockEmbeddings
from langchain_aws.vectorstores import AmazonS3Vectors
from langchain_core.embeddings import Embeddings
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

# Module-level embedding cache (persists across requests)
_embedding_cache: dict[str, list[float]] = {}
_CACHE_MAX_SIZE = 1000


def _get_cache_key(text: str) -> str:
    """Create a hash key for caching embeddings."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class CachedBedrockEmbeddings(Embeddings):
    """
    Wrapper around BedrockEmbeddings with LRU caching.

    Caches embedding results to avoid repeated API calls for identical queries.
    Inherits from LangChain's Embeddings base class for compatibility with FAISS and other vector stores.
    """

    def __init__(self, embeddings: BedrockEmbeddings) -> None:
        logger.info(f"{__name__}:CachedBedrockEmbeddings.__init__ - Initializing with embeddings type={type(embeddings).__name__}")
        self._embeddings = embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents with caching."""
        logger.info(f"{__name__}:embed_documents - START: Caching {len(texts)} texts")
        results = []
        uncached_texts = []
        uncached_indices = []

        # Check cache first
        for i, text in enumerate(texts):
            key = _get_cache_key(text)
            if key in _embedding_cache:
                results.append(_embedding_cache[key])
                logger.debug(f"{__name__}:embed_documents - Cache HIT for text hash {key}")
            else:
                results.append(None)  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Fetch uncached embeddings
        if uncached_texts:
            logger.info(f"{__name__}:embed_documents - Cache MISS: fetching {len(uncached_texts)} embeddings from base embeddings")
            try:
                new_embeddings = self._embeddings.embed_documents(uncached_texts)
                logger.info(f"{__name__}:embed_documents - Received {len(new_embeddings)} embeddings from base")

                # Store in cache and results
                for idx, text, embedding in zip(uncached_indices, uncached_texts, new_embeddings, strict=True):
                    key = _get_cache_key(text)
                    if len(_embedding_cache) < _CACHE_MAX_SIZE:
                        _embedding_cache[key] = embedding
                    results[idx] = embedding
            except Exception as e:
                logger.error(f"{__name__}:embed_documents - FAILED to embed documents: {type(e).__name__}: {e}", exc_info=True)
                raise
        else:
            logger.info(f"{__name__}:embed_documents - All {len(texts)} embeddings from cache")

        logger.info(f"{__name__}:embed_documents - SUCCESS: Returning {len(results)} embeddings")
        return results

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query with caching."""
        logger.info(f"{__name__}:embed_query - START: Query text_len={len(text)}")
        key = _get_cache_key(text)

        if key in _embedding_cache:
            logger.info(f"{__name__}:embed_query - Cache HIT for query (key={key[:8]}...)")
            return _embedding_cache[key]

        logger.info(f"{__name__}:embed_query - Cache MISS: calling Bedrock API")
        try:
            embedding = self._embeddings.embed_query(text)
            logger.info(f"{__name__}:embed_query - Received embedding from Bedrock (dim={len(embedding)})")

            if len(_embedding_cache) < _CACHE_MAX_SIZE:
                _embedding_cache[key] = embedding
                logger.info(f"{__name__}:embed_query - Cached embedding (cache_size={len(_embedding_cache)})")

            return embedding
        except Exception as e:
            logger.error(f"{__name__}:embed_query - FAILED to embed query: {type(e).__name__}: {e}", exc_info=True)
            raise


def _is_throttling_error(exception: BaseException) -> bool:
    """Check if exception is a Bedrock throttling error."""
    if isinstance(exception, ClientError):
        error_code = exception.response.get("Error", {}).get("Code", "")
        return error_code in ("ThrottlingException", "TooManyRequestsException")
    # Also catch throttling wrapped in other exceptions
    return "ThrottlingException" in str(exception) or "Too many requests" in str(exception)


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
        embedding_region: str = "us-east-1",
        embedding_model_id: str = "amazon.titan-embed-text-v2:0",
    ) -> None:
        """
        Initialize S3 Vectors store with Bedrock embeddings.

        Args:
            vectors_bucket: S3 Vectors bucket name
            index_name: Index name within the bucket
            region: AWS region for S3 Vectors
            embedding_region: AWS region for Bedrock embeddings (us-east-1 has higher quota)
            embedding_model_id: Bedrock embedding model ID
        """
        self._vectors_bucket = vectors_bucket
        self._index_name = index_name
        self._region = region
        self._embedding_region = embedding_region

        # Create boto3 client with NO internal retries
        # This lets our tenacity retry control all backoff behavior
        no_retry_config = Config(
            retries={"max_attempts": 0, "mode": "standard"},
            read_timeout=30,
            connect_timeout=10,
        )
        bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=embedding_region,  # Use separate region for embeddings
            config=no_retry_config,
        )

        logger.info(
            f"{__name__}:__init__ - Creating BedrockEmbeddings in {embedding_region} (S3 Vectors in {region})"
        )

        base_embeddings = BedrockEmbeddings(
            model_id=embedding_model_id,
            region_name=embedding_region,  # Use separate region for embeddings
            client=bedrock_client,  # Use our no-retry client
        )

        # Wrap with cache to reduce API calls
        self._embeddings = CachedBedrockEmbeddings(base_embeddings)
        logger.info(f"{__name__}:__init__ - Using CachedBedrockEmbeddings wrapper")

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

        Includes exponential backoff retry for Bedrock throttling errors.

        Args:
            query: Search query text
            k: Number of results to return
            session_id: Filter by session ID (for multi-tenant isolation)
            doc_id: Filter by document ID

        Returns:
            list[VectorSearchResult]: Search results with scores and metadata

        Raises:
            ClientError: After max retries exhausted for throttling
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
            if _is_throttling_error(e):
                logger.error(f"{__name__}:similarity_search - ThrottlingException: Max retries exhausted")
            else:
                logger.error(f"{__name__}:similarity_search - {type(e).__name__}: {e}")
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
