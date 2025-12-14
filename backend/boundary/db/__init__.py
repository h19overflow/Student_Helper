"""
Database boundary layer: ORM models and connection management.

Exports:
  - Base, UUIDMixin, TimestampMixin: Model building blocks
  - get_engine(), get_session_factory(), get_db(): Connection management
  - SessionModel, DocumentModel, JobModel: Core domain entities
  - JobStatus, JobType, DocumentStatus: Enum types for state tracking

Dependencies: sqlalchemy, backend.configs
System role: Database adapter providing persistent storage for sessions,
documents, and background jobs with auto-lifecycle management.
"""

from backend.boundary.db.base import Base, TimestampMixin, UUIDMixin
from backend.boundary.db.connection import get_db, get_engine, get_session_factory
from backend.boundary.db.models.session_model import SessionModel
from backend.boundary.db.models.document_model import DocumentModel
from backend.boundary.db.models.job_model import JobModel, JobStatus, JobType

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    "get_db",
    "get_engine",
    "get_session_factory",
    "SessionModel",
    "DocumentModel",
    "JobModel",
    "JobStatus",
    "JobType",
]
