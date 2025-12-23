"""
Session ORM model.

Represents a user session with associated chat history and documents.
Sessions isolate retrieval scope for RAG operations.

Dependencies: sqlalchemy, backend.boundary.db.base
System role: Session persistence for chat context management
"""

from uuid import UUID
from sqlalchemy import String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.boundary.db.base import Base, UUIDMixin, TimestampMixin


class SessionModel(Base, UUIDMixin, TimestampMixin):
    """
    Session ORM model for isolating chat and document scope.

    Each session represents a user conversation context. Documents are
    scoped to sessions to ensure RAG retrieval only uses relevant documents.
    Visual knowledge diagrams (images) are also scoped to sessions.
    Cascade delete ensures orphaned documents and images are cleaned up.

    Attributes:
        id: UUID primary key (auto-generated)
        metadata: JSONB field storing session-specific data (user, preferences, tags)
        documents: List of DocumentModel rows for this session (cascading delete)
        images: List of ImageModel rows (visual diagrams) for this session (cascading delete)
        created_at: Session creation timestamp (UTC)
        updated_at: Last modification timestamp (UTC)

    Relationships:
        documents: One-to-many with DocumentModel (cascade delete on session removal)
        images: One-to-many with ImageModel (cascade delete on session removal)
    """

    __tablename__ = "sessions"

    session_metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Flexible session metadata (user info, preferences, etc.)",
    )

    course_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
        doc="Parent course ID (optional, for course-based sessions)"
    )

    # Relationships
    course = relationship(
        "CourseModel",
        back_populates="sessions",
        foreign_keys=[course_id]
    )
    documents = relationship(
        "DocumentModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    images = relationship(
        "ImageModel",
        back_populates="session",
        cascade="all, delete-orphan",
    )
