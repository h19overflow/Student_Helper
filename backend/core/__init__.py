"""
Core business logic module.

Contains domain business logic, exception hierarchy, and core components.
All business rules and domain-specific logic reside here.
"""

from backend.core.exceptions import (
    LegalSearchException,
    ValidationError,
    SessionNotFoundError,
    DocumentProcessingError,
    ParsingError,
    EmbeddingError,
    VectorStoreError,
    RetrievalError,
    ObservabilityError,
)

# Business logic modules
from backend.core.document_processing import DocumentPipeline
from backend.core.session import JobTracker, SessionManager
# Note: observability module available for LangFuse integration

__all__ = [
    # Exceptions
    "LegalSearchException",
    "ValidationError",
    "SessionNotFoundError",
    "DocumentProcessingError",
    "ParsingError",
    "EmbeddingError",
    "VectorStoreError",
    "RetrievalError",
    "ObservabilityError",
    # Business logic
    "DocumentPipeline",
    "JobTracker",
    "SessionManager",
]
