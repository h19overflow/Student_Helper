"""
Document ORM model.

Represents uploaded documents with processing status and metadata.
Tracks document ingestion lifecycle from upload to vector storage.

Dependencies: sqlalchemy, backend.boundary.db.base
System role: Document persistence for ingestion tracking
"""

import enum
from sqlalchemy import String, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from backend.boundary.db.base import Base, UUIDMixin, TimestampMixin


class DocumentStatus(str, enum.Enum):
    """
    Document processing lifecycle states.

    PENDING: Document uploaded, awaiting ingestion task
    PROCESSING: Lambda worker is parsing, chunking, and embedding
    COMPLETED: Successfully indexed in vector store, ready for retrieval
    FAILED: Processing error; error_message field contains details
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentModel(Base, UUIDMixin, TimestampMixin):
    """
    Document ORM model tracking ingestion pipeline state.

    Lifecycle: Upload (PENDING) → Lambda processing (PROCESSING) → Vector
    indexing (COMPLETED) or failure (FAILED). Status transitions trigger
    observability events for monitoring and debugging.

    Attributes:
        id: UUID primary key (auto-generated)
        session_id: Foreign key to SessionModel (cascade delete)
        name: Original filename (255 char limit)
        status: Current processing state (enum: PENDING/PROCESSING/COMPLETED/FAILED)
        upload_url: S3 URL or file path pointing to raw document (1024 char limit)
        error_message: Null if success; human-readable error if FAILED (2048 char limit)
        created_at: Document upload timestamp (UTC)
        updated_at: Last status change timestamp (UTC)

    Relationships:
        session: Parent SessionModel (back_populates=documents)

    Constraints:
        session_id: Foreign key ON DELETE CASCADE to sessions.id
    """

    __tablename__ = "documents"

    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original filename",
    )

    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, native_enum=False),
        nullable=False,
        default=DocumentStatus.PENDING,
    )

    upload_url: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        doc="S3 URL or file path for raw document",
    )

    error_message: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        doc="Error details if processing failed",
    )

    # Relationships
    session = relationship("SessionModel", back_populates="documents")
