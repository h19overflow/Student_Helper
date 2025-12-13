"""
Diagram API endpoints.

Routes: POST /sessions/{id}/diagram

Dependencies: backend.application.diagram_service, backend.models
System role: Diagram generation HTTP API
"""

from fastapi import APIRouter, Depends
import uuid

router = APIRouter(prefix="/sessions", tags=["diagrams"])


@router.post("/{session_id}/diagram")
async def generate_diagram(session_id: uuid.UUID):
    """Generate Mermaid diagram for session."""
    pass
