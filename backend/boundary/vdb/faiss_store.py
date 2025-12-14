"""
Local FAISS vector store for development.

Provides a local vector store using FAISS-CPU for testing document
processing pipeline without AWS S3 Vectors dependency.

Dependencies: langchain_community.vectorstores, langchain_aws
System role: Development vector store (local testing only)
"""

from pathlib import Path
from typing import Any
import uuid

from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from backend.boundary.vdb.vector_schemas import (
    VectorMetadata,
    VectorQuery,
    VectorSearchResult,
)


class FAISSStore:
    """
    Local FAISS vector store for development testing.

    Wraps LangChain FAISS with interface compatible with VectorStoreClient.
    Stores index locally for persistence across runs.
    """

    def __init__(
        self,
        persist_directory: str = ".faiss_index",
        model_id: str = "amazon.titan-embed-text-v2:0",
        region: str = "us-east-1",
    ) -> None:
        """
        Initialize FAISS store with Bedrock embeddings.

        Args:
            persist_directory: Directory for FAISS index persistence
            model_id: Bedrock embedding model ID
            region: AWS region for Bedrock
        """
        self._persist_dir = Path(persist_directory)
        self._persist_dir.mkdir(parents=True, exist_ok=True)

        self._embeddings = BedrockEmbeddings(
            model_id=model_id,
            region_name=region,
        )

        self._index: FAISS | None = None
        self._load_or_create_index()

    def _load_or_create_index(self) -> None:
        """Load existing index or create empty one."""
        index_path = self._persist_dir / "index.faiss"
        if index_path.exists():
            self._index = FAISS.load_local(
                str(self._persist_dir),
                self._embeddings,
                allow_dangerous_deserialization=True,
            )

    def add_documents(
        self,
        documents: list[Document],
        session_id: str | None = None,
        doc_id: str | None = None,
    ) -> list[str]:
        """
        Add documents to FAISS index.

        Args:
            documents: LangChain Documents with content and metadata
            session_id: Session ID for metadata filtering
            doc_id: Document ID for metadata filtering

        Returns:
            list[str]: Generated document IDs
        """
        if not documents:
            return []

        for doc in documents:
            doc.metadata["session_id"] = session_id or str(uuid.uuid4())
            doc.metadata["doc_id"] = doc_id or str(uuid.uuid4())

        if self._index is None:
            self._index = FAISS.from_documents(documents, self._embeddings)
        else:
            self._index.add_documents(documents)

        self._index.save_local(str(self._persist_dir))

        return [doc.metadata.get("doc_id", "") for doc in documents]

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        session_id: str | None = None,
        doc_id: str | None = None,
    ) -> list[VectorSearchResult]:
        """
        Search for similar documents.

        Args:
            query: Search query text
            k: Number of results to return
            session_id: Filter by session ID
            doc_id: Filter by document ID

        Returns:
            list[VectorSearchResult]: Search results with scores
        """
        if self._index is None:
            return []

        filter_dict: dict[str, Any] = {}
        if session_id:
            filter_dict["session_id"] = session_id
        if doc_id:
            filter_dict["doc_id"] = doc_id

        results = self._index.similarity_search_with_score(
            query,
            k=k,
            filter=filter_dict if filter_dict else None,
        )

        search_results = []
        for doc, score in results:
            metadata = doc.metadata
            search_results.append(
                VectorSearchResult(
                    chunk_id=metadata.get("chunk_id", str(uuid.uuid4())),
                    content=doc.page_content,
                    metadata=VectorMetadata(
                        session_id=uuid.UUID(metadata.get("session_id", str(uuid.uuid4()))),
                        doc_id=uuid.UUID(metadata.get("doc_id", str(uuid.uuid4()))),
                        chunk_id=metadata.get("chunk_id", ""),
                        page=metadata.get("page"),
                        section=metadata.get("section"),
                        source_uri=metadata.get("source", ""),
                    ),
                    similarity_score=float(1 - score),
                )
            )

        return search_results

    def delete_by_doc_id(self, doc_id: str) -> None:
        """
        Delete all vectors for a document.

        Args:
            doc_id: Document ID to delete
        """
        if self._index is None:
            return

        ids_to_delete = []
        for doc_id_in_store, doc in self._index.docstore._dict.items():
            if doc.metadata.get("doc_id") == doc_id:
                ids_to_delete.append(doc_id_in_store)

        if ids_to_delete:
            self._index.delete(ids_to_delete)
            self._index.save_local(str(self._persist_dir))

    def clear(self) -> None:
        """Clear all vectors from index."""
        self._index = None
        index_path = self._persist_dir / "index.faiss"
        pkl_path = self._persist_dir / "index.pkl"
        if index_path.exists():
            index_path.unlink()
        if pkl_path.exists():
            pkl_path.unlink()
