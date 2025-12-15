"""
Dependency injection container.

Factory functions for FastAPI dependencies.

Dependencies: backend.configs, backend.application, backend.boundary
System role: DI container for service injection
"""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.configs import Settings, get_settings
from backend.boundary.db import get_async_db
from backend.application.services import (
    DiagramService,
    DocumentService,
    JobService,
    SessionService,
)


@lru_cache
def get_settings_dependency() -> Settings:
    """Get settings singleton."""
    return get_settings()


def get_session_service(db: AsyncSession = Depends(get_async_db)) -> SessionService:
    """
    Get session service instance.

    Args:
        db: Async database session (injected via Depends)

    Returns:
        SessionService: Session service instance
    """
    return SessionService(db=db)


def get_document_service(db: AsyncSession = Depends(get_async_db)) -> DocumentService:
    """
    Get document service instance.

    Args:
        db: Async database session (injected via Depends)

    Returns:
        DocumentService: Document service instance with DevDocumentPipeline
    """
    from backend.boundary.vdb.dev_task import DevDocumentPipeline

    dev_pipeline = DevDocumentPipeline(
        chunk_size=1000,
        chunk_overlap=200,
        persist_directory=".faiss_index",
    )
    return DocumentService(db=db, dev_pipeline=dev_pipeline)


def get_job_service(db: AsyncSession = Depends(get_async_db)) -> JobService:
    """
    Get job service instance.

    Args:
        db: Async database session (injected via Depends)

    Returns:
        JobService: Job service instance
    """
    return JobService(db=db)


def get_chat_service(db: AsyncSession = Depends(get_async_db)):
    """
    Get chat service instance with RAG agent.

    Args:
        db: Async database session (injected via Depends)

    Returns:
        ChatService: Chat service with configured RAG agent
    """
    # Lazy import to avoid loading torch/transformers at startup
    from backend.application.services import ChatService
    from backend.boundary.vdb.faiss_store import FAISSStore
    from backend.core.agentic_system.agent.rag_agent import RAGAgent

    # Create vector store
    vector_store = FAISSStore(
        persist_directory=".faiss_index",
        model_id="amazon.titan-embed-text-v2:0",
        region="ap-southeast-2",
    )

    # Create RAG agent
    rag_agent = RAGAgent(
        vector_store=vector_store,
        model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        region="ap-southeast-2",
        temperature=0.0,
    )

    return ChatService(db=db, rag_agent=rag_agent)


def get_diagram_service() -> DiagramService:
    """
    Get diagram service instance.

    Returns:
        DiagramService: Diagram service instance
    """
    return DiagramService()
