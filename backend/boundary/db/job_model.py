"""
Job ORM model.

Tracks Celery task execution for async operations (ingestion, evaluation).
Provides job status and progress reporting.

Dependencies: sqlalchemy, backend.boundary.db.base
System role: Async job tracking for background tasks
"""

import enum
from sqlalchemy import String, Enum, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.boundary.db.base import Base, UUIDMixin, TimestampMixin


class JobType(str, enum.Enum):
    """Job type enum."""

    DOCUMENT_INGESTION = "document_ingestion"
    EVALUATION = "evaluation"


class JobStatus(str, enum.Enum):
    """Job status enum."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobModel(Base, UUIDMixin, TimestampMixin):
    """
    Job ORM model for Celery task tracking.

    Attributes:
        id: UUID primary key
        task_id: Celery task ID
        type: Job type enum
        status: Job status enum
        progress: Progress percentage (0-100)
        result: JSONB field for job results or error details
        created_at: Timestamp of job creation
        updated_at: Timestamp of last status update
    """

    __tablename__ = "jobs"

    task_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        doc="Celery task ID for correlation",
    )

    type: Mapped[JobType] = mapped_column(
        Enum(JobType, native_enum=False),
        nullable=False,
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False),
        nullable=False,
        default=JobStatus.PENDING,
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Progress percentage (0-100)",
    )

    result: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Job results or error details",
    )
