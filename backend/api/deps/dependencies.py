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
        DocumentService: Document service instance with S3 Vectors pipeline
    """
    # Pipeline and vector store are lazy-loaded in DocumentService
    return DocumentService(db=db)


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
    # Lazy import to avoid loading heavy dependencies at startup
    from backend.application.services import ChatService
    from backend.boundary.vdb.s3_vectors_store import S3VectorsStore
    from backend.core.agentic_system.agent.rag_agent import RAGAgent

    # Create vector store
    vector_store = S3VectorsStore(
        vectors_bucket="student-helper-dev-vectors",
        index_name="documents",
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


def get_s3_document_client():
    """
    Get S3 document client for presigned URL generation.

    Returns:
        S3DocumentClient: Client for document bucket operations
    """
    from backend.boundary.aws.s3_client import S3DocumentClient

    settings = get_settings()
    return S3DocumentClient(
        bucket=settings.s3_documents.bucket,
        region=settings.s3_documents.region,
    )
