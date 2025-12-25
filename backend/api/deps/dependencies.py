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
from backend.boundary.aws.s3_client import S3DocumentClient
from backend.application.services import (
    DiagramService,
    DocumentService,
    JobService,
    SessionService,
)
from backend.application.services.course_service import CourseService
from backend.application.services.visual_knowledge_service import (
    VisualKnowledgeService,
)


class ServiceCache:
    """Container for cached service instances."""
    
    def __init__(self):
        self._vector_store = None
        self._rag_agent = None
        self._document_pipeline = None
        self._s3_client = None
        self._diagram_service = None
    
    @property
    def vector_store(self):
        """Get cached vector store."""
        if self._vector_store is None:
            from backend.boundary.vdb.vector_store_factory import get_vector_store
            self._vector_store = get_vector_store()
        return self._vector_store
    
    @property
    def rag_agent(self):
        """Get cached RAG agent."""
        if self._rag_agent is None:
            from backend.core.agentic_system.agent.rag_agent import RAGAgent
            
            # Using hardcoded values as they are not currently available in settings
            self._rag_agent = RAGAgent(
                vector_store=self.vector_store,
                model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
                region="ap-southeast-2",
                temperature=0.0,
            )
        return self._rag_agent

    @property
    def document_pipeline(self):
        """Get cached document pipeline."""
        if self._document_pipeline is None:
            from backend.core.document_processing.entrypoint import DocumentPipeline
            self._document_pipeline = DocumentPipeline()
        return self._document_pipeline

    @property
    def s3_client(self):
        """Get cached S3 document client."""
        if self._s3_client is None:
            from backend.boundary.aws.s3_client import S3DocumentClient
            
            settings = get_settings()
            self._s3_client = S3DocumentClient(
                bucket=settings.s3_documents.bucket,
                region=settings.s3_documents.region,
            )
        return self._s3_client

    @property
    def diagram_service(self):
        """Get cached diagram service."""
        if self._diagram_service is None:
            from backend.application.services import DiagramService
            self._diagram_service = DiagramService()
        return self._diagram_service
    
    def clear(self) -> None:
        """Clear all cached instances."""
        self._vector_store = None
        self._rag_agent = None
        self._document_pipeline = None
        self._s3_client = None
        self._diagram_service = None


# Global service cache
_service_cache = ServiceCache()

def get_service_cache() -> ServiceCache:
    """Get service cache singleton."""
    return _service_cache


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


def get_course_service(db: AsyncSession = Depends(get_async_db)) -> CourseService:
    """
    Get course service instance.

    Args:
        db: Async database session (injected via Depends)

    Returns:
        CourseService: Course service instance
    """
    return CourseService(db=db)


def get_document_service(db: AsyncSession = Depends(get_async_db)) -> DocumentService:
    """
    Get document service instance.

    Args:
        db: Async database session (injected via Depends)

    Returns:
        DocumentService: Document service instance with S3 Vectors pipeline
    """
    cache = get_service_cache()
    return DocumentService(
        db=db,
        pipeline=cache.document_pipeline,
        vector_store=cache.vector_store,
    )


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

    cache = get_service_cache()
    return ChatService(db=db, rag_agent=cache.rag_agent)


def get_s3_document_client():
    """
    Get S3 document client for presigned URL generation.

    Returns:
        S3DocumentClient: Client for document bucket operations
    """
    cache = get_service_cache()
    return cache.s3_client


def get_visual_knowledge_service(
    db: AsyncSession = Depends(get_async_db),
    s3_client: S3DocumentClient = Depends(get_s3_document_client),
) -> VisualKnowledgeService:
    """
    Get visual knowledge service instance.

    Uses vector store selected via VECTOR_STORE_TYPE env var.
    Initializes Gemini client, curation agent, and S3 client for presigned URLs.

    Args:
        db: Async database session (injected)
        s3_client: S3DocumentClient for presigned URL generation (injected)

    Returns:
        VisualKnowledgeService: Visual knowledge service with configured agent and S3 client
    """
    import os

    from backend.core.agentic_system.visual_knowledge_agent.visual_knowledge_agent import (
        VisualKnowledgeAgent,
    )

    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")

    cache = get_service_cache()

    agent = VisualKnowledgeAgent(
        google_api_key=google_api_key,
        vector_store=cache.vector_store,
        db_session=db,
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
    cache = get_service_cache()
    return cache.diagram_service
