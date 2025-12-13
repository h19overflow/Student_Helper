"""
Dependency injection container.

Factory functions for FastAPI dependencies.

Dependencies: backend.configs, backend.application, backend.boundary
System role: DI container for service injection
"""

from functools import lru_cache
from sqlalchemy.orm import Session

from backend.configs import Settings, get_settings
from backend.boundary.db import get_db
from backend.application.services import (
    DiagramService,
    DocumentService,
    JobService,
    RetrievalService,
    SessionService,
)


@lru_cache
def get_settings_dependency() -> Settings:
    """Get settings singleton."""
    return get_settings()


def get_session_service(db: Session = get_db()) -> SessionService:
    """
    Get session service instance.

    Args:
        db: Database session

    Returns:
        SessionService: Session service instance
    """
    pass


def get_document_service(db: Session = get_db()) -> DocumentService:
    """
    Get document service instance.

    Args:
        db: Database session

    Returns:
        DocumentService: Document service instance
    """
    pass


def get_job_service(db: Session = get_db()) -> JobService:
    """
    Get job service instance.

    Args:
        db: Database session

    Returns:
        JobService: Job service instance
    """
    pass


def get_retrieval_service() -> RetrievalService:
    """
    Get retrieval service instance.

    Returns:
        RetrievalService: Retrieval service instance
    """
    pass


def get_diagram_service() -> DiagramService:
    """
    Get diagram service instance.

    Returns:
        DiagramService: Diagram service instance
    """
    pass
