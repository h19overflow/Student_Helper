"""
Database boundary layer.

Provides SQLAlchemy ORM models, database connection management,
and session factory for PostgreSQL operations.

Dependencies: sqlalchemy, backend.configs
System role: Database adapter for persistence layer
"""

from backend.boundary.db.base import Base, TimestampMixin, UUIDMixin
from backend.boundary.db.connection import get_db, get_engine, get_session_factory
from backend.boundary.db.session_model import SessionModel
from backend.boundary.db.document_model import DocumentModel
from backend.boundary.db.job_model import JobModel, JobStatus, JobType

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
