"""
Document service orchestrator.

Coordinates document upload and status tracking.

Dependencies: backend.core, backend.boundary.db
System role: Document management orchestration
"""

from sqlalchemy.orm import Session
import uuid


class DocumentService:
    """Document service orchestrator."""

    def __init__(self, db: Session) -> None:
        """Initialize document service."""
        pass

    def upload_documents(self, session_id: uuid.UUID, files: list[str]) -> list[uuid.UUID]:
        """Upload documents and trigger ingestion."""
        pass

    def get_documents(self, session_id: uuid.UUID, cursor: str | None = None) -> dict:
        """Get paginated document list."""
        pass

    def get_document_status(self, doc_id: uuid.UUID) -> dict:
        """Get document processing status."""
        pass
