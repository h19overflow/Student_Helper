"""
WebSocket streaming chat endpoint.

Provides real-time token streaming for chat responses using WebSocket.

Routes: WS /ws/sessions/{session_id}/chat

Dependencies: backend.application.services.chat_service
System role: WebSocket streaming HTTP API
"""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.application.services.chat_service import ChatService
from backend.models.streaming import (
    ClientEventType,
    StreamEventType,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["streaming"])


@router.websocket("/ws/sessions/{session_id}/chat")
async def websocket_chat(
    websocket: WebSocket,
    session_id: UUID,
) -> None:
    """
    WebSocket endpoint for streaming chat responses.

    Client sends:
        {"event": "chat", "data": {"message": "...", "include_diagram": false}}
        {"event": "ping"}

    Server sends:
        {"event": "connected", "data": {"session_id": "..."}}
        {"event": "context", "data": {"chunks": [...]}}
        {"event": "token", "data": {"token": "...", "index": 0}}
        {"event": "citations", "data": {"citations": [...]}}
        {"event": "complete", "data": {"full_answer": "..."}}
        {"event": "error", "data": {"code": "...", "message": "..."}}

    Args:
        websocket: WebSocket connection
        session_id: Session UUID from path
    """
    logger.info(
        "WebSocket connection established",
        extra={"session_id": str(session_id), "client_host": websocket.client},
    )

    await websocket.accept()

    # Send connected event
    await websocket.send_json({
        "event": StreamEventType.CONNECTED.value,
        "data": {"session_id": str(session_id)},
    })

    # Import inside function to avoid circular imports and startup loading
    from backend.application.services import ChatService
    from backend.boundary.db import get_async_session_factory

    try:
        while True:
            # Receive message from client
            raw_data = await websocket.receive_text()
            logger.debug(
                "Raw WebSocket message received",
                extra={
                    "session_id": str(session_id),
                    "raw_data_length": len(raw_data),
                    "raw_data_preview": raw_data[:100] if len(raw_data) <= 100 else raw_data[:97] + "...",
                },
            )

            try:
                data = json.loads(raw_data)
                logger.debug(
                    "JSON parsed successfully",
                    extra={
                        "session_id": str(session_id),
                        "event_keys": list(data.keys()) if isinstance(data, dict) else "not-dict",
                    },
                )
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse JSON",
                    extra={
                        "session_id": str(session_id),
                        "error_msg": str(e),
                        "raw_data_preview": raw_data[:50],
                    },
                )
                await websocket.send_json({
                    "event": StreamEventType.ERROR.value,
                    "data": {"code": "INVALID_JSON", "message": "Invalid JSON format"},
                })
                continue

            event_type = data.get("event")
            logger.debug(
                "Event type extracted",
                extra={
                    "session_id": str(session_id),
                    "event_type": str(event_type),
                    "event_type_class": type(event_type).__name__,
                },
            )

            if event_type == ClientEventType.PING.value:
                logger.debug("Ping event received", extra={"session_id": str(session_id)})
                await websocket.send_json({"event": "pong"})
                continue

            if event_type == ClientEventType.CHAT.value:
                logger.info(
                    "Chat event received",
                    extra={"session_id": str(session_id)},
                )
                event_data = data.get("data", {})
                logger.debug(
                    "Chat event data extracted",
                    extra={
                        "session_id": str(session_id),
                        "data_keys": list(event_data.keys()) if isinstance(event_data, dict) else "not-dict",
                        "data_type": type(event_data).__name__,
                    },
                )

                message = event_data.get("message")
                logger.debug(
                    "Message extracted from event data",
                    extra={
                        "session_id": str(session_id),
                        "message_type": type(message).__name__,
                        "message_length": len(message) if isinstance(message, str) else "not-string",
                    },
                )

                if not message:
                    logger.warning(
                        "Chat message is missing or empty",
                        extra={"session_id": str(session_id), "message_value": message},
                    )
                    await websocket.send_json({
                        "event": StreamEventType.ERROR.value,
                        "data": {"code": "MISSING_MESSAGE", "message": "Message is required"},
                    })
                    continue

                # Create services for this request
                logger.info(
                    "Initializing chat services",
                    extra={"session_id": str(session_id)},
                )

                try:
                    async with get_async_session_factory()() as db:
                        logger.debug("Database session created", extra={"session_id": str(session_id)})

                        # Get shared vector store and RAG agent from app state
                        # These are initialized once at app startup and reused across all requests
                        rag_agent = websocket.app.state.rag_agent

                        logger.debug(
                            "Using shared resources from app state",
                            extra={"session_id": str(session_id)},
                        )

                        chat_service = ChatService(db=db, rag_agent=rag_agent)
                        logger.debug("Chat service initialized", extra={"session_id": str(session_id)})

                        try:
                            # Stream chat response
                            logger.info(
                                "Starting chat stream",
                                extra={"session_id": str(session_id), "message_length": len(message)},
                            )
                            event_count = 0
                            async for event in chat_service.stream_chat(
                                session_id=session_id,
                                message=message,
                            ):
                                event_count += 1
                                logger.debug(
                                    "Chat event streamed",
                                    extra={
                                        "session_id": str(session_id),
                                        "event_number": event_count,
                                        "event_type": type(event).__name__,
                                    },
                                )
                                await websocket.send_json(event.to_dict())

                            logger.info(
                                "Chat stream completed",
                                extra={
                                    "session_id": str(session_id),
                                    "total_events": event_count,
                                },
                            )

                        except ValueError as e:
                            # Session not found or validation error
                            logger.warning(
                                "Validation error during chat stream",
                                extra={
                                    "session_id": str(session_id),
                                    "error_type": type(e).__name__,
                                    "error_msg": str(e),
                                },
                            )
                            await websocket.send_json({
                                "event": StreamEventType.ERROR.value,
                                "data": {"code": "SESSION_NOT_FOUND", "message": str(e)},
                            })

                        except Exception as e:
                            # Generic processing error
                            logger.exception(
                                "Unexpected error during chat stream",
                                extra={
                                    "session_id": str(session_id),
                                    "error_type": type(e).__name__,
                                    "error_msg": str(e),
                                },
                            )
                            await websocket.send_json({
                                "event": StreamEventType.ERROR.value,
                                "data": {"code": "PROCESSING_ERROR", "message": str(e)},
                            })

                except Exception as e:
                    logger.exception(
                        "Error initializing chat services",
                        extra={
                            "session_id": str(session_id),
                            "error_type": type(e).__name__,
                            "error_msg": str(e),
                        },
                    )
                    await websocket.send_json({
                        "event": StreamEventType.ERROR.value,
                        "data": {"code": "SERVICE_ERROR", "message": f"Failed to initialize services: {str(e)}"},
                    })

            else:
                # Log details about unknown event for debugging
                logger.warning(
                    "Unknown event type received",
                    extra={
                        "session_id": str(session_id),
                        "event_type": str(event_type) if event_type else "None",
                        "event_type_class": type(event_type).__name__ if event_type else "NoneType",
                        "full_data": str(data)[:200],  # Truncate for logging
                    },
                )
                try:
                    event_str = str(event_type)
                    await websocket.send_json({
                        "event": StreamEventType.ERROR.value,
                        "data": {"code": "UNKNOWN_EVENT", "message": f"Unknown event type: {event_str}"},
                    })
                except TypeError as e:
                    logger.error(
                        "Failed to format unknown event error message",
                        extra={
                            "session_id": str(session_id),
                            "error": str(e),
                            "event_type_raw": repr(event_type),
                        },
                    )
                    await websocket.send_json({
                        "event": StreamEventType.ERROR.value,
                        "data": {"code": "UNKNOWN_EVENT", "message": "Unknown event type (unable to format)"},
                    })

    except WebSocketDisconnect:
        logger.info(
            "WebSocket client disconnected",
            extra={"session_id": str(session_id)},
        )
    except Exception as e:
        logger.exception(
            "Unexpected error in WebSocket handler",
            extra={
                "session_id": str(session_id),
                "error_type": type(e).__name__,
                "error_msg": str(e),
            },
        )
