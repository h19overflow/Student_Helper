"""API-specific dependencies."""

# Re-export common dependencies from backend.dependencies
from backend.dependencies import (
    get_diagram_service,
    get_document_service,
    get_job_service,
    get_retrieval_service,
    get_session_service,
    get_settings_dependency,
)

__all__ = [
    "get_diagram_service",
    "get_document_service",
    "get_job_service",
    "get_retrieval_service",
    "get_session_service",
    "get_settings_dependency",
]
