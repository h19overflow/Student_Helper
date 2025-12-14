"""
Chat service for conversational Q&A with RAG.

Orchestrates full chat flow: history retrieval, RAG invocation, message persistence.
Integrates ChatHistoryAdapter for PostgreSQL message storage and RAGAgent for Q&A.

Dependencies: backend.core.agentic_system, backend.application.adapters, backend.boundary.db
System role: Chat service orchestration layer
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.adapters.chat_history_adapter import ChatHistoryAdapter
from backend.boundary.db.CRUD.session_crud import session_crud
from backend.core.agentic_system.agent.rag_agent import RAGAgent
from backend.core.agentic_system.agent.rag_agent_schema import RAGResponse


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
