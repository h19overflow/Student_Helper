"""
Retrieval service orchestrator.

Coordinates RAG retrieval operations.

Dependencies: backend.core.retriever, backend.boundary.vdb
System role: Retrieval orchestration
"""

import uuid


class RetrievalService:
    """Retrieval service orchestrator."""

    def __init__(self) -> None:
        """Initialize retrieval service."""
        pass

    def retrieve_for_query(self, query: str, session_id: uuid.UUID) -> list[dict]:
        """Retrieve chunks for query."""
        pass

    def retrieve_with_filters(
        self,
        query: str,
        session_id: uuid.UUID,
        doc_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Retrieve chunks with metadata filters."""
        pass
