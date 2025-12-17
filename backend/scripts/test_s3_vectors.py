"""
Test script for S3 Vectors integration.

Tests real document upload and search with mocked session context.
Run: python -m backend.scripts.test_s3_vectors

Dependencies: backend.core.document_processing, backend.boundary.vdb
"""

import uuid
from pathlib import Path

from backend.core.document_processing.entrypoint import DocumentPipeline
from backend.boundary.vdb.s3_vectors_store import S3VectorsStore


def test_upload_and_search():
    """Test document upload to S3 Vectors and similarity search."""
    session_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())

    file_path = Path("Hamza_CV.pdf")
    if not file_path.exists():
        file_path = Path(__file__).parent.parent.parent / "Hamza_CV.pdf"

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    pipeline = DocumentPipeline()
    result = pipeline.process(
        file_path=str(file_path),
        document_id=document_id,
        session_id=session_id,
    )

    vector_store = S3VectorsStore()

    test_queries = [
        "What is Hamza's experience?",
        "What programming languages does Hamza know?",
        "What projects has Hamza worked on?",
    ]

    for query in test_queries:
        results = vector_store.similarity_search(
            query=query,
            k=3,
            session_id=session_id,
        )

    results = vector_store.similarity_search(
        query="Hamza experience",
        k=3,
        session_id=None,
    )

    return {
        "session_id": session_id,
        "document_id": result.document_id,
        "chunk_count": result.chunk_count,
        "output_path": result.output_path,
    }


def test_search_only(session_id: str | None = None):
    """Test search on existing documents."""
    vector_store = S3VectorsStore()

    results = vector_store.similarity_search(
        query="What is Hamza's experience with Python?",
        k=5,
        session_id=session_id,
    )

    return [
        {
            "chunk_id": r.chunk_id,
            "score": r.similarity_score,
            "session_id": r.metadata.session_id,
            "content_preview": r.content[:200],
        }
        for r in results
    ]


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--search-only":
        session_id = sys.argv[2] if len(sys.argv) > 2 else None
        test_search_only(session_id)
    else:
        test_upload_and_search()
