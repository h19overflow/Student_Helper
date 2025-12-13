"""
Session ORM model.

Represents a user session with associated chat history and documents.
Sessions isolate retrieval scope for RAG operations.

Dependencies: sqlalchemy, backend.boundary.db.base
System role: Session persistence for chat context management
"""

from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.boundary.db.base import Base, UUIDMixin, TimestampMixin


class SessionModel(Base, UUIDMixin, TimestampMixin):
    """
    Session ORM model.

    Attributes:
        id: UUID primary key
        metadata: JSONB field for flexible session metadata
        documents: Relationship to documents in this session
        created_at: Timestamp of session creation
        updated_at: Timestamp of last session update
    """

    __tablename__ = "sessions"

    metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Flexible session metadata (user info, preferences, etc.)",
    )

    # Relationships
    documents = relationship(
        "DocumentModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )
