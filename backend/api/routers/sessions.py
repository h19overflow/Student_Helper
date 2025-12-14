"""
Session API endpoints.

Routes: POST /sessions, GET /sessions, POST /sessions/{id}/chat

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
from backend.models.chat import ChatRequest, ChatResponse
from backend.models.citation import Citation
from backend.models.session import CreateSessionRequest, SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    session_service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    """
    Create new session with optional metadata.

    Args:
        request: CreateSessionRequest with metadata field
        session_service: Injected SessionService

    Returns:
        SessionResponse: Created session

    Raises:
        HTTPException(400): Invalid request
        HTTPException(500): Creation failed
    """
    try:
        session_id = await session_service.create_session(metadata=request.metadata)
        session_data = await session_service.get_session(session_id)
        return SessionResponse(**session_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Session creation failed: {str(e)}"
        )


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    limit: int = 100,
    offset: int = 0,
    session_service: SessionService = Depends(get_session_service),
) -> list[SessionResponse]:
    """
    List all sessions with pagination.

    Args:
        limit: Maximum number of sessions (default 100)
        offset: Number to skip (default 0)
        session_service: Injected SessionService

    Returns:
        list[SessionResponse]: List of sessions

    Raises:
        HTTPException(500): Retrieval failed
    """
    try:
        sessions = await session_service.get_all_sessions(limit=limit, offset=offset)
        return [SessionResponse(**session) for session in sessions]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve sessions: {str(e)}"
        )


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
