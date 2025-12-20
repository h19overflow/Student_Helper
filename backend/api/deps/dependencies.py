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

    Uses vector store selected via VECTOR_STORE_TYPE env var (FAISS for dev, S3 for prod).

    Args:
        db: Async database session (injected via Depends)

    Returns:
        ChatService: Chat service with configured RAG agent
    """
    # Lazy import to avoid loading heavy dependencies at startup
    from backend.application.services import ChatService
    from backend.boundary.vdb.vector_store_factory import get_vector_store
    from backend.core.agentic_system.agent.rag_agent import RAGAgent

    # Get vector store based on environment (FAISS for dev, S3 for prod)
    vector_store = get_vector_store()

    # Create RAG agent (vector_store param now optional - will auto-select if None)
    rag_agent = RAGAgent(
        vector_store=vector_store,
        model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        region="ap-southeast-2",
        temperature=0.0,
    )

    return ChatService(db=db, rag_agent=rag_agent)


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


def get_visual_knowledge_service(
    s3_client=Depends(get_s3_document_client),
):
    """
    Get visual knowledge service instance.

    Uses vector store selected via VECTOR_STORE_TYPE env var.
    Initializes Gemini client, curation agent, and S3 client for presigned URLs.

    Args:
        s3_client: S3DocumentClient for presigned URL generation (injected)

    Returns:
        VisualKnowledgeService: Visual knowledge service with configured agent and S3 client
    """
    import os

    from backend.application.services.visual_knowledge_service import (
        VisualKnowledgeService,
    )
    from backend.boundary.vdb.vector_store_factory import get_vector_store
    from backend.core.agentic_system.visual_knowledge_agent.visual_knowledge_agent import (
        VisualKnowledgeAgent,
    )

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")

    vector_store = get_vector_store()

    agent = VisualKnowledgeAgent(
        google_api_key=google_api_key,
        vector_store=vector_store,
        model_id="gemini-3-flash-preview",
        temperature=0.0,
    )

    return VisualKnowledgeService(
        visual_knowledge_agent=agent,
        s3_client=s3_client,
    )


def get_diagram_service() -> DiagramService:
    """
    Get diagram service instance.

    Returns:
        DiagramService: Diagram service instance
    """
    return DiagramService()
