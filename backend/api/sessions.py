"""
Session API endpoints.

Routes: POST /sessions, POST /sessions/{id}/chat

Dependencies: backend.application.session_service, backend.models
System role: Session HTTP API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import uuid

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("")
async def create_session(db: Session = Depends()):
    """Create new session."""
    pass


@router.post("/{session_id}/chat")
async def chat(session_id: uuid.UUID, db: Session = Depends()):
    """Send chat message to session."""
    pass
