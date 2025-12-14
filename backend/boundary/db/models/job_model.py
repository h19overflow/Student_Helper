"""
Job ORM model.

Tracks Lambda task execution for async operations (ingestion, evaluation).
Provides job status and progress reporting via SQS message correlation.

Dependencies: sqlalchemy, backend.boundary.db.base
System role: Async job tracking for background tasks
"""

import enum
from sqlalchemy import String, Enum, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.boundary.db.base import Base, UUIDMixin, TimestampMixin


class JobType(str, enum.Enum):
    """
    Background job types for Lambda task classification.

    DOCUMENT_INGESTION: Parse, chunk, embed document; index in vector store
    EVALUATION: Assess document quality, relevance, or generate metrics
    """

    DOCUMENT_INGESTION = "document_ingestion"
    EVALUATION = "evaluation"


class JobStatus(str, enum.Enum):
    """
    Lambda task execution states.

    PENDING: Task enqueued in SQS, awaiting worker pickup
    RUNNING: Lambda worker processing the task
    COMPLETED: Task succeeded; check result field for output
    FAILED: Task failed; check result field for error details
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobModel(Base, UUIDMixin, TimestampMixin):
    """
    Job ORM model linking SQS messages to Lambda task results.

    Correlates async SQS messages with job status updates from Lambda workers.
    Enables frontend polling (via /jobs/{id}) to show task progress without
    WebSockets. Result field stores success payload or error stack trace.

    Attributes:
        id: UUID primary key (auto-generated)
        task_id: SQS MessageId for worker correlation (unique constraint)
        type: Job classification enum (DOCUMENT_INGESTION/EVALUATION)
        status: Current execution state enum (PENDING/RUNNING/COMPLETED/FAILED)
        progress: Percentage complete (0-100); updated during long tasks
        result: JSONB field; on success contains job output, on failure contains
                error details or stack trace (empty dict {} on creation)
        created_at: Job enqueue timestamp (UTC)
        updated_at: Last status update timestamp (UTC)

    Constraints:
        task_id: UNIQUE constraint; one job per SQS message

    Workflow:
        1. API enqueues SQS message, creates JobModel with task_id, status=PENDING
        2. Lambda worker retrieves SQS message, updates status → RUNNING, progress → X
        3. Lambda completes, updates status → COMPLETED/FAILED, populates result
        4. Frontend polls /jobs/{id} to fetch latest status
    """

    __tablename__ = "jobs"

    task_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        doc="SQS message ID for Lambda correlation",
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
