"""
FAISS vector store for local development.

Provides same interface as S3VectorsStore but uses local FAISS index.
Supports session filtering and metadata-based retrieval.
Uses Google Gemini embeddings for consistency with production.

Dependencies: faiss-cpu, backend.boundary.vdb.embeddings_wrapper, backend.boundary.vdb.vector_schemas
System role: Local vector store for development RAG
"""

import logging
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import FAISS

from backend.boundary.vdb.embeddings_wrapper import FixedDimensionEmbeddings
from backend.boundary.vdb.vector_schemas import (
    VectorMetadata,
    VectorSearchResult,
)

logger = logging.getLogger(__name__)

# Local index path - use /tmp in production for Docker compatibility
# The directory is created lazily in __init__ to avoid permission errors at import time
import os
FAISS_INDEX_DIR = Path(os.getenv("FAISS_INDEX_DIR", "/tmp/.faiss_index"))


class FAISSVectorsStore:
    """
    FAISS vector store for local development.

    Wraps LangChain FAISS with session filtering and metadata support.
    Persists index to disk for reuse across runs.
    Uses Google Gemini embeddings for consistency with production.
    """

    def __init__(
        self,
        index_name: str = "local-dev",
        region: str = "ap-southeast-2",
        embedding_region: str = "us-east-1",
        embedding_model_id: str = "models/gemini-embedding-001",
        embedding_dimension: int = 1024,
    ) -> None:
        """
        Initialize FAISS vector store with Google Gemini embeddings.

        Args:
            index_name: Local index name
            region: AWS region (used for consistency, not needed for FAISS)
            embedding_region: Unused - kept for backwards compatibility
            embedding_model_id: Google embedding model ID (default: gemini-embedding-001)
            embedding_dimension: Output dimension for embeddings (default: 1024)
        """
        self._index_name = index_name
        self._region = region

        logger.info(
            f"{__name__}:__init__ - Creating FixedDimensionEmbeddings with "
            f"model={embedding_model_id}, dimension={embedding_dimension}"
        )

        # Use wrapper that enforces consistent dimensions on all embed calls
        self._embeddings = FixedDimensionEmbeddings(
            model=embedding_model_id,
            output_dimensionality=embedding_dimension,
        )
        logger.info(f"{__name__}:__init__ - FixedDimensionEmbeddings initialized")

        # Create index directory if it doesn't exist
        FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)

        # Load or initialize FAISS index
        self._vector_store = self._load_or_create_index()

    def _load_or_create_index(self) -> FAISS:
        """Load existing FAISS index or create new one."""
        try:
            logger.info(f"{__name__}:_load_or_create_index - START: Attempting to load existing index from {FAISS_INDEX_DIR}")
            self._vector_store = FAISS.load_local(
                str(FAISS_INDEX_DIR),
                self._embeddings,
                index_name=self._index_name,
            )
            logger.info(f"{__name__}:_load_or_create_index - SUCCESS: Index loaded successfully")
            return self._vector_store
        except Exception as e:
            logger.info(f"{__name__}:_load_or_create_index - Index load failed ({type(e).__name__}): {e}, creating new index")

        # Create empty index with a dummy document
        logger.info(f"{__name__}:_load_or_create_index - Creating new FAISS index")
        try:
            logger.info(f"{__name__}:_load_or_create_index - Step 1: Generating dummy embedding")
            dummy_embedding = self._embeddings.embed_query("dummy")
            logger.info(f"{__name__}:_load_or_create_index - Step 1 OK: dummy_embedding type={type(dummy_embedding)}, length={len(dummy_embedding) if isinstance(dummy_embedding, list) else 'N/A'}")

            import faiss
            logger.info(f"{__name__}:_load_or_create_index - Step 2: Creating FAISS index with dimension={len(dummy_embedding)}")

            dimension = len(dummy_embedding)
            index = faiss.IndexFlatL2(dimension)
            logger.info(f"{__name__}:_load_or_create_index - Step 2 OK: FAISS IndexFlatL2 created")

            logger.info(f"{__name__}:_load_or_create_index - Step 3: Creating FAISS wrapper (embedding_function type={type(self._embeddings).__name__})")
            vector_store = FAISS(
                embedding_function=self._embeddings,
                index=index,
                docstore={},
                index_to_docstore_id={},
            )
            logger.info(f"{__name__}:_load_or_create_index - Step 3 OK: FAISS wrapper created")

            logger.info(f"{__name__}:_load_or_create_index - Step 4: Saving index to {FAISS_INDEX_DIR}")
            vector_store.save_local(str(FAISS_INDEX_DIR), index_name=self._index_name)
            logger.info(f"{__name__}:_load_or_create_index - Step 4 OK: Index saved")

            return vector_store
        except Exception as e:
            logger.error(f"{__name__}:_load_or_create_index - FAILED during index creation: {type(e).__name__}: {e}", exc_info=True)
            raise

    def _filter_results(
        self,
        results: list[tuple],
        session_id: str | None = None,
        doc_id: str | None = None,
    ) -> list[tuple]:
        """Filter results by metadata (session_id, doc_id)."""
        filtered = []
        for doc, score in results:
            metadata = doc.metadata or {}
            if session_id and metadata.get("session_id") != session_id:
                continue
            if doc_id and metadata.get("doc_id") != doc_id:
                continue
            filtered.append((doc, score))
        return filtered

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
            session_id: Filter by session ID
            doc_id: Filter by document ID

        Returns:
            list[VectorSearchResult]: Search results with scores and metadata
        """
        logger.info(f"{__name__}:similarity_search - START: query_len={len(query)}, k={k}, session_id={session_id}, doc_id={doc_id}")
        try:
            # Fetch more results to account for filtering
            fetch_k = k * 3 if (session_id or doc_id) else k
            logger.info(f"{__name__}:similarity_search - Step 1: Fetching {fetch_k} results (fetch_k for filtering)")

            logger.info(f"{__name__}:similarity_search - Step 1a: vector_store type={type(self._vector_store).__name__}")
            results = self._vector_store.similarity_search_with_score(
                query=query,
                k=fetch_k,
            )
            logger.info(f"{__name__}:similarity_search - Step 1 OK: Retrieved {len(results)} raw results")

            # Apply filtering
            logger.info(f"{__name__}:similarity_search - Step 2: Applying filters (session_id={session_id}, doc_id={doc_id})")
            filtered_results = self._filter_results(results, session_id, doc_id)
            filtered_results = filtered_results[:k]
            logger.info(f"{__name__}:similarity_search - Step 2 OK: Filtered to {len(filtered_results)} results (capped at k={k})")

            # Build response
            logger.info(f"{__name__}:similarity_search - Step 3: Building VectorSearchResult objects")
            search_results = []
            for idx, (doc, score) in enumerate(filtered_results):
                try:
                    metadata = doc.metadata or {}
                    logger.debug(f"{__name__}:similarity_search - Processing result {idx}: chunk_id={metadata.get('chunk_id')}, score={score}")
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
                except Exception as e:
                    logger.error(f"{__name__}:similarity_search - Failed to process result {idx}: {type(e).__name__}: {e}", exc_info=True)
                    raise

            logger.info(
                f"{__name__}:similarity_search - SUCCESS: Built {len(search_results)} results",
                extra={"session_id": session_id, "k": k},
            )
            return search_results

        except Exception as e:
            logger.error(f"{__name__}:similarity_search - FAILED: {type(e).__name__}: {e}", exc_info=True)
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
        try:
            results = self._vector_store.max_marginal_relevance_search(
                query=query,
                k=k,
                fetch_k=fetch_k,
                lambda_mult=lambda_mult,
            )

            # Apply session filtering
            if session_id:
                results = [
                    doc for doc in results
                    if (doc.metadata or {}).get("session_id") == session_id
                ][:k]

            search_results = []
            for doc in results:
                metadata = doc.metadata or {}
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
                        similarity_score=1.0,
                    )
                )

            return search_results

        except Exception as e:
            logger.error(f"{__name__}:max_marginal_relevance_search - {type(e).__name__}: {e}")
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
            VectorStoreRetriever: LangChain retriever
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
            self._vector_store.save_local(str(FAISS_INDEX_DIR), index_name=self._index_name)
            logger.info(
                "Deleted document chunks",
                extra={"doc_id": doc_id, "chunk_count": len(chunk_ids)},
            )
        except Exception as e:
            logger.error(
                "Failed to delete document chunks",
                extra={"doc_id": doc_id, "error": str(e)},
            )
            raise

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> list[str]:
        """
        Add documents to the FAISS index.

        Args:
            texts: Document texts
            metadatas: Document metadata
            ids: Document IDs

        Returns:
            list[str]: Added document IDs
        """
        try:
            doc_ids = self._vector_store.add_texts(
                texts=texts,
                metadatas=metadatas,
                ids=ids,
            )
            self._vector_store.save_local(str(FAISS_INDEX_DIR), index_name=self._index_name)
            logger.info(f"{__name__}:add_documents - Added {len(doc_ids)} documents")
            return doc_ids
        except Exception as e:
            logger.error(f"{__name__}:add_documents - {type(e).__name__}: {e}")
            raise
