"""Chat API endpoints.

Routes:
- POST /sessions/{session_id}/chat - Send chat message with RAG context
- POST /sessions/{session_id}/chat/stream - Stream chat response using Server-Sent Events (SSE)

Dependencies: backend.application.services.chat_service, backend.application.services.diagram_service
System role: Chat messaging HTTP API with streaming support
"""

import json
import logging
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from backend.application.services.chat_service import ChatService
from backend.application.services.diagram_service import DiagramService
from backend.api.deps import (
    get_chat_service,
    get_diagram_service,
)
from backend.models.chat import (
    ChatRequest,
    ChatResponse,
)
from backend.models.citation import Citation
from backend.models.streaming import StreamEventType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["chat"])


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat(
    session_id: UUID,
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
    diagram_service: DiagramService = Depends(get_diagram_service),
) -> ChatResponse:
    """Send chat message to session with conversational memory.

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


@router.post("/{session_id}/chat/stream")
async def chat_stream(
    session_id: UUID,
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    """Stream chat response using Server-Sent Events (SSE).

    Works through HTTP API Gateway (no WebSocket required).
    Streams tokens in real-time for responsive UI.

    SSE Format:
        event: context
        data: {"chunks": [...]}

        event: token
        data: {"token": "...", "index": 0}

        event: citations
        data: {"citations": [...]}

        event: complete
        data: {"full_answer": "..."}

        event: error
        data: {"code": "...", "message": "..."}

    Args:
        session_id: Session UUID
        request: ChatRequest with message
        chat_service: Injected ChatService

    Returns:
        StreamingResponse: SSE stream of chat events
    """
    logger.info(f"{__name__}:chat_stream - START session_id={session_id}")

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from chat stream."""
        try:
            async for event in chat_service.stream_chat(
                session_id=session_id,
                message=request.message,
                context_window_size=10,
            ):
                # Format as SSE: "event: {type}\ndata: {json}\n\n"
                event_type = event.event.value
                event_data = json.dumps(event.data)
                yield f"event: {event_type}\ndata: {event_data}\n\n"

            logger.info(f"{__name__}:chat_stream - Stream completed for session_id={session_id}")

        except ValueError as e:
            # Session not found
            logger.error(f"{__name__}:chat_stream - ValueError: {e}")
            error_data = json.dumps({"code": "SESSION_NOT_FOUND", "message": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

        except Exception as e:
            # Generic error
            logger.error(f"{__name__}:chat_stream - {type(e).__name__}: {e}")
            error_data = json.dumps({"code": "PROCESSING_ERROR", "message": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
