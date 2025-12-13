"""
Document API endpoints.

Routes: POST /sessions/{id}/docs, GET /sessions/{id}/docs

Dependencies: backend.application.document_service, backend.models
System role: Document HTTP API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import uuid

router = APIRouter(prefix="/sessions", tags=["documents"])


@router.post("/{session_id}/docs")
async def upload_documents(session_id: uuid.UUID, db: Session = Depends()):
    """Upload documents to session."""
    pass


@router.get("/{session_id}/docs")
async def get_documents(session_id: uuid.UUID, cursor: str | None = None, db: Session = Depends()):
    """Get paginated document list."""
    pass
