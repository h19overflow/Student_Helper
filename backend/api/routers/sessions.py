"""
Session API endpoints.

Routes:
- POST /sessions - Create new session
- GET /sessions - List all sessions
- DELETE /sessions/{id} - Delete session
- GET /sessions/{id}/chat/history - Get chat history

Dependencies: backend.application.session_service, backend.models
System role: Session management HTTP API
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.application.services.chat_service import ChatService
from backend.application.services.session_service import SessionService
from backend.api.deps import (
    get_chat_service,
    get_session_service,
)
from backend.models.chat import (
    ChatHistoryResponse,
    ChatMessageResponse,
)
from backend.models.session import CreateSessionRequest, SessionResponse

logger = logging.getLogger(__name__)

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
        # Ensure metadata dict is not None
        metadata = request.metadata or {}
        session_id = await session_service.create_session(metadata=metadata)
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


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: UUID,
    session_service: SessionService = Depends(get_session_service),
) -> None:
    """
    Delete session by ID.

    Args:
        session_id: Session UUID
        session_service: Injected SessionService

    Returns:
        204 No Content on success

    Raises:
        HTTPException(404): Session not found
        HTTPException(500): Deletion failed
    """
    try:
        await session_service.delete_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Session deletion failed: {str(e)}"
        )


@router.get("/{session_id}/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: UUID,
    limit: int = 100,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatHistoryResponse:
    """
    Get chat history for a session.

    Args:
        session_id: Session UUID
        limit: Maximum number of messages to return (default 100)
        chat_service: Injected ChatService

    Returns:
        ChatHistoryResponse: List of messages with total count

    Raises:
        HTTPException(404): Session not found
        HTTPException(500): Retrieval failed
    """
    from backend.application.adapters.chat_history_adapter import ChatHistoryAdapter

    try:
        chat_adapter = ChatHistoryAdapter(session_id=session_id, db=chat_service.db)
        messages = await chat_adapter.get_messages_as_dicts(limit=limit)

        # Map role names: "human" -> "user", "ai" -> "assistant"
        chat_messages = [
            ChatMessageResponse(
                role="user" if msg["role"] == "human" else "assistant",
                content=msg["content"],
            )
            for msg in messages
        ]

        return ChatHistoryResponse(
            messages=chat_messages,
            total=len(chat_messages),
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve chat history: {str(e)}",
        )
