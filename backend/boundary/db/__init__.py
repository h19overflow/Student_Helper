"""
Database boundary layer: ORM models, CRUD operations, and connection management.

Exports:
  - Base, UUIDMixin, TimestampMixin: Model building blocks
  - get_engine(), get_session_factory(), get_db(): Sync connection management
  - get_async_engine(), get_async_session_factory(), get_async_db(): Async connection management
  - SessionModel, DocumentModel, JobModel: Core domain entities
  - JobStatus, JobType, DocumentStatus: Enum types for state tracking
  - session_crud, document_crud, job_crud: CRUD operation singletons

Dependencies: sqlalchemy, backend.configs
System role: Database adapter providing persistent storage for sessions,
documents, and background jobs with auto-lifecycle management.
"""

from backend.boundary.db.base import Base, TimestampMixin, UUIDMixin
from backend.boundary.db.connection import (
    get_db,
    get_engine,
    get_session_factory,
    get_async_db,
    get_async_engine,
    get_async_session_factory,
)
from backend.boundary.db.models.session_model import SessionModel
from backend.boundary.db.models.document_model import DocumentModel, DocumentStatus
from backend.boundary.db.models.job_model import JobModel, JobStatus, JobType
from backend.boundary.db.CRUD import (
    BaseCRUD,
    SessionCRUD,
    DocumentCRUD,
    JobCRUD,
    session_crud,
    document_crud,
    job_crud,
)

__all__ = [
    # Base classes
    "Base",
    "TimestampMixin",
    "UUIDMixin",
    # Connection
    "get_db",
    "get_engine",
    "get_session_factory",
    "get_async_db",
    "get_async_engine",
    "get_async_session_factory",
    # Models
    "SessionModel",
    "DocumentModel",
    "DocumentStatus",
    "JobModel",
    "JobStatus",
    "JobType",
    # CRUD classes
    "BaseCRUD",
    "SessionCRUD",
    "DocumentCRUD",
    "JobCRUD",
    # CRUD singletons
    "session_crud",
    "document_crud",
    "job_crud",
]
