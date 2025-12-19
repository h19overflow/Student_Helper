"""
Chat service for conversational Q&A with RAG.

Orchestrates full chat flow: history retrieval, RAG invocation, message persistence.
Integrates ChatHistoryAdapter for PostgreSQL message storage and RAGAgent for Q&A.
Supports streaming via stream_chat() for WebSocket real-time responses.

Dependencies: backend.core.agentic_system, backend.application.adapters, backend.boundary.db
System role: Chat service orchestration layer
"""

import logging
from collections.abc import AsyncGenerator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.adapters.chat_history_adapter import ChatHistoryAdapter
from backend.boundary.db.CRUD.session_crud import session_crud
from backend.core.agentic_system.agent.rag_agent import RAGAgent
from backend.core.agentic_system.agent.rag_agent_schema import RAGResponse
from backend.models.streaming import StreamEvent, StreamEventType

logger = logging.getLogger(__name__)


class ChatService:
    """
    Chat service for conversational Q&A.

    Coordinates session validation, chat history retrieval, RAG agent invocation,
    and message persistence for multi-turn conversations.
    """

    def __init__(
        self,
        db: AsyncSession,
        rag_agent: RAGAgent,
    ) -> None:
        """
        Initialize chat service.

        Args:
            db: AsyncSession for database operations
            rag_agent: RAG agent instance for Q&A
        """
        self.db = db
        self.rag_agent = rag_agent

    async def process_chat(
        self,
        session_id: UUID,
        message: str,
        context_window_size: int = 10,
    ) -> RAGResponse:
        """
        Process chat message through full conversation flow.

        Flow:
        1. Validate session exists
        2. Fetch recent chat history (context window)
        3. Invoke RAG agent with message and history
        4. Store user message and AI response
        5. Return RAG response

        Args:
            session_id: Session UUID
            message: User's message
            context_window_size: Number of recent messages to include as context

        Returns:
            RAGResponse: Answer with citations, confidence, and reasoning

        Raises:
            ValueError: If session does not exist
        """
        # Validate session exists
        session = await session_crud.get_by_id(self.db, session_id)
        if not session:
            raise ValueError(f"Session {session_id} does not exist")

        # Create chat history adapter for this session
        chat_adapter = ChatHistoryAdapter(session_id=session_id, db=self.db)

        # Fetch recent conversation history
        chat_history = await chat_adapter.get_messages(limit=context_window_size)

        # Invoke RAG agent with question and history
        rag_response = await self.rag_agent.ainvoke(
            question=message,
            session_id=str(session_id),
            chat_history=chat_history,
        )

        # Store user message
        await chat_adapter.add_user_message(message)

        # Store AI response
        await chat_adapter.add_ai_message(rag_response.answer)

        return rag_response

    async def stream_chat(
        self,
        session_id: UUID,
        message: str,
        context_window_size: int = 10,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream chat response tokens for real-time WebSocket delivery.

        Flow:
        1. Validate session exists
        2. Fetch recent chat history
        3. Stream events from RAG agent
        4. Store messages after completion

        Args:
            session_id: Session UUID
            message: User's message
            context_window_size: Number of recent messages for context

        Yields:
            StreamEvent: Context, token, citations, and complete events

        Raises:
            ValueError: If session does not exist
        """
        logger.info(f"{__name__}:stream_chat - START session_id={session_id}")

        # Step 1: Validate session exists
        try:
            logger.info(f"{__name__}:stream_chat - Validating session exists")
            session = await session_crud.get_by_id(self.db, session_id)
            if not session:
                logger.error(f"{__name__}:stream_chat - Session not found: {session_id}")
                raise ValueError(f"Session {session_id} does not exist")
            logger.info(f"{__name__}:stream_chat - Session validated OK")
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"{__name__}:stream_chat - Session validation failed: {type(e).__name__}: {e}")
            raise

        # Step 2: Create chat history adapter
        try:
            logger.info(f"{__name__}:stream_chat - Creating chat history adapter")
            chat_adapter = ChatHistoryAdapter(session_id=session_id, db=self.db)
            logger.info(f"{__name__}:stream_chat - Chat adapter created OK")
        except Exception as e:
            logger.error(f"{__name__}:stream_chat - Chat adapter creation failed: {type(e).__name__}: {e}")
            raise

        # Step 3: Fetch recent conversation history
        try:
            logger.info(f"{__name__}:stream_chat - Fetching chat history (limit={context_window_size})")
            chat_history = await chat_adapter.get_messages(limit=context_window_size)
            logger.info(f"{__name__}:stream_chat - Chat history fetched: {len(chat_history)} messages")
        except Exception as e:
            logger.error(f"{__name__}:stream_chat - Chat history fetch failed: {type(e).__name__}: {e}")
            raise

        # Step 4: Store user message before streaming starts
        try:
            logger.info(f"{__name__}:stream_chat - Storing user message (len={len(message)})")
            await chat_adapter.add_user_message(message)
            logger.info(f"{__name__}:stream_chat - User message stored OK")
        except Exception as e:
            logger.error(f"{__name__}:stream_chat - User message storage failed: {type(e).__name__}: {e}")
            raise

        # Step 5: Stream from RAG agent
        full_answer = ""
        event_count = 0

        try:
            logger.info(f"{__name__}:stream_chat - Starting RAG agent stream")
            async for event in self.rag_agent.astream(
                question=message,
                session_id=str(session_id),
                chat_history=chat_history,
            ):
                event_count += 1
                if event_count <= 3 or event.event == StreamEventType.COMPLETE:
                    logger.info(f"{__name__}:stream_chat - Event #{event_count}: {event.event.value}")

                yield event

                # Capture full answer from complete event
                if event.event == StreamEventType.COMPLETE:
                    full_answer = event.data.get("full_answer", "")
                    logger.info(f"{__name__}:stream_chat - COMPLETE event, answer_len={len(full_answer)}")

            logger.info(f"{__name__}:stream_chat - RAG stream finished, total_events={event_count}")

        except Exception as e:
            logger.error(f"{__name__}:stream_chat - RAG agent stream failed: {type(e).__name__}: {e}")
            raise

        # Step 6: Store AI response after streaming completes
        try:
            if full_answer:
                logger.info(f"{__name__}:stream_chat - Storing AI response (len={len(full_answer)})")
                await chat_adapter.add_ai_message(full_answer)
                logger.info(f"{__name__}:stream_chat - AI response stored OK")
            else:
                logger.warning(f"{__name__}:stream_chat - No full_answer to store (empty response)")
        except Exception as e:
            logger.error(f"{__name__}:stream_chat - AI response storage failed: {type(e).__name__}: {e}")
            raise

        logger.info(f"{__name__}:stream_chat - END session_id={session_id}")
