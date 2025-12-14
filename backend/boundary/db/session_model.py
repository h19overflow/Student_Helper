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
    Session ORM model for isolating chat and document scope.

    Each session represents a user conversation context. Documents are
    scoped to sessions to ensure RAG retrieval only uses relevant documents.
    Cascade delete ensures orphaned documents are cleaned up.

    Attributes:
        id: UUID primary key (auto-generated)
        metadata: JSONB field storing session-specific data (user, preferences, tags)
        documents: List of DocumentModel rows for this session (cascading delete)
        created_at: Session creation timestamp (UTC)
        updated_at: Last modification timestamp (UTC)

    Relationships:
        documents: One-to-many with DocumentModel (cascade delete on session removal)
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
