"""
Session API endpoints.

Routes: POST /sessions, POST /sessions/{id}/chat

Dependencies: backend.application.session_service, backend.models
System role: Session HTTP API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.application.services.chat_service import ChatService
from backend.application.services.diagram_service import DiagramService
from backend.application.services.session_service import SessionService
from backend.api.deps import (
    get_chat_service,
    get_diagram_service,
    get_session_service,
)
from backend.boundary.db import get_db
from backend.models.chat import ChatRequest, ChatResponse
from backend.models.citation import Citation

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("")
async def create_session(
    session_service: SessionService = Depends(get_session_service),
):
    """Create new session."""
    # Placeholder - implement when SessionService is ready
    pass


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat(
    session_id: UUID,
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    diagram_service: DiagramService = Depends(get_diagram_service),
) -> ChatResponse:
    """
    Send chat message to session with conversational memory.

    Flow:
    1. Process chat through ChatService (validates session, retrieves history, invokes RAG)
    2. Optionally generate Mermaid diagram
    3. Map RAGResponse to ChatResponse
    4. Return answer with citations

    Args:
        session_id: Session UUID
        request: ChatRequest with message and optional diagram flag
        chat_service: Injected ChatService
        diagram_service: Injected DiagramService

    Returns:
        ChatResponse: Answer with citations and optional diagram

    Raises:
        HTTPException(404): Session not found
        HTTPException(500): Processing error
    """
    try:
        # Process chat message through service
        rag_response = await chat_service.process_chat(
            session_id=session_id,
            message=request.message,
            context_window_size=10,
        )

        # Generate diagram if requested
        mermaid_diagram = None
        if request.include_diagram:
            diagram_result = diagram_service.generate_diagram(
                prompt=request.message,
                session_id=session_id,
            )
            mermaid_diagram = diagram_result.get("diagram_code")

        # Map RAGCitation to Citation
        citations = [
            Citation(
                doc_name=cite.source_uri.split("/")[-1],  # Extract filename
                page=cite.page,
                section=cite.section,
                chunk_id=cite.chunk_id,
                source_uri=cite.source_uri,
            )
            for cite in rag_response.citations
        ]

        return ChatResponse(
            answer=rag_response.answer,
            citations=citations,
            mermaid_diagram=mermaid_diagram,
        )

    except ValueError as e:
        # Session not found or validation error
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Generic processing error
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {str(e)}",
        )
