"""
Development task for local document processing pipeline testing.

Integrates document parsing, chunking, and FAISS storage for local
development without AWS S3 Vectors dependency.

Dependencies: backend.core.document_processing, backend.boundary.vdb
System role: Local development testing entry point
"""

import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from backend.core.document_processing.tasks.parsing_task import ParsingTask
from backend.core.document_processing.tasks.chunking_task import ChunkingTask
from backend.boundary.vdb.faiss_store import FAISSStore


@dataclass
class DevPipelineResult:
    """Result from development pipeline processing."""

    document_id: str
    chunk_count: int
    processing_time_ms: float
    index_path: str


class DevDocumentPipeline:
    """
    Development document pipeline using local FAISS storage.

    Pipeline stages:
    1. Parse document (Docling)
    2. Chunk text (RecursiveCharacterTextSplitter)
    3. Embed and store (FAISS + Bedrock)
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        persist_directory: str = ".faiss_index",
        embedding_model_id: str = "amazon.titan-embed-text-v2:0",
        bedrock_region: str = "us-east-1",
    ) -> None:
        """
        Initialize development pipeline.

        Args:
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between consecutive chunks
            persist_directory: Directory for FAISS index persistence
            embedding_model_id: Bedrock embedding model ID
            bedrock_region: AWS region for Bedrock
        """
        self._parsing_task = ParsingTask()
        self._chunking_task = ChunkingTask(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        self._faiss_store = FAISSStore(
            persist_directory=persist_directory,
            model_id=embedding_model_id,
            region=bedrock_region,
        )
        self._persist_dir = persist_directory

    def process(
        self,
        file_path: str,
        document_id: str | None = None,
        session_id: str | None = None,
    ) -> DevPipelineResult:
        """
        Process document through local development pipeline.

        Args:
            file_path: Path to document file
            document_id: Optional document ID (generated if None)
            session_id: Optional session ID (generated if None)

        Returns:
            DevPipelineResult: Processing result with chunk count

        Raises:
            ParsingError: Document parsing failed
            ValueError: Chunking failed
        """
        start_time = time.perf_counter()
        doc_id = document_id or str(uuid.uuid4())
        sess_id = session_id or str(uuid.uuid4())

        documents = self._parsing_task.parse(file_path)

        chunked_documents = self._chunking_task.chunk(documents)

        for i, doc in enumerate(chunked_documents):
            doc.metadata["chunk_id"] = f"{doc_id}_{i}"
            doc.metadata["chunk_index"] = i

        self._faiss_store.add_documents(
            chunked_documents,
            session_id=sess_id,
            doc_id=doc_id,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return DevPipelineResult(
            document_id=doc_id,
            chunk_count=len(chunked_documents),
            processing_time_ms=elapsed_ms,
            index_path=self._persist_dir,
        )

    def search(
        self,
        query: str,
        k: int = 5,
        session_id: str | None = None,
        doc_id: str | None = None,
    ) -> list[dict]:
        """
        Search indexed documents.

        Args:
            query: Search query text
            k: Number of results
            session_id: Filter by session
            doc_id: Filter by document

        Returns:
            list[dict]: Search results with content and metadata
        """
        results = self._faiss_store.similarity_search(
            query=query,
            k=k,
            session_id=session_id,
            doc_id=doc_id,
        )
        return [
            {
                "content": r.content,
                "score": r.similarity_score,
                "metadata": r.metadata.model_dump(),
            }
            for r in results
        ]

    def clear_index(self) -> None:
        """Clear all indexed documents."""
        self._faiss_store.clear()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m backend.boundary.vdb.dev_task <file_path> [query]")
        sys.exit(1)

    file_path = sys.argv[1]

    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    pipeline = DevDocumentPipeline()

    print(f"Processing: {file_path}")
    result = pipeline.process(file_path)
    print(f"Document ID: {result.document_id}")
    print(f"Chunks: {result.chunk_count}")
    print(f"Time: {result.processing_time_ms:.2f}ms")
    print(f"Index: {result.index_path}")

    if len(sys.argv) > 2:
        query = sys.argv[2]
        print(f"\nSearching: {query}")
        search_results = pipeline.search(query, k=3)
        for i, r in enumerate(search_results, 1):
            print(f"\n--- Result {i} (score: {r['score']:.3f}) ---")
            print(r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"])
