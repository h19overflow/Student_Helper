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
    """Document processing status enum."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentModel(Base, UUIDMixin, TimestampMixin):
    """
    Document ORM model.

    Attributes:
        id: UUID primary key
        session_id: Foreign key to session
        name: Document filename
        status: Processing status enum
        upload_url: S3 URL or file path for raw document
        error_message: Error details if status is FAILED
        created_at: Timestamp of upload
        updated_at: Timestamp of last status update
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
