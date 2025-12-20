"""
Image ORM model for visual knowledge diagrams.

Represents generated concept diagrams with S3 storage and curation metadata.
Tracks diagram generation and links images to sessions and chat messages.

Dependencies: sqlalchemy, backend.boundary.db.base
System role: Image persistence for visual knowledge diagrams
"""

from sqlalchemy import String, JSON, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from backend.boundary.db.base import Base, UUIDMixin, TimestampMixin


class ImageModel(Base, UUIDMixin, TimestampMixin):
    """
    Image ORM model for visual knowledge diagrams.

    Each image represents a concept diagram generated from an AI response.
    Images are scoped to sessions and optionally linked to specific chat messages.
    Stores curation metadata and S3 location for efficient retrieval.

    Attributes:
        id: UUID primary key (auto-generated)
        session_id: Foreign key to SessionModel (cascade delete)
        s3_key: S3 object key for image location (e.g., sessions/{session_id}/images/{image_id}.png)
        mime_type: Image MIME type (e.g., image/png, image/jpeg) for correct rendering
        message_index: Optional position in chat history for linking to specific AI message
        main_concepts: JSON array of 2-3 main concept strings extracted during curation
        branches: JSON array of branch objects with id, label, description for exploration
        image_generation_prompt: Full prompt sent to Gemini for audit trail and regeneration
        created_at: Image generation timestamp (UTC)
        updated_at: Last modification timestamp (UTC)

    Relationships:
        session: Parent SessionModel (back_populates=images)

    Constraints:
        session_id: Foreign key ON DELETE CASCADE to sessions.id
    """

    __tablename__ = "images"

    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        doc="Session this image belongs to",
    )

    s3_key: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        doc="S3 object key for image location (e.g., sessions/{session_id}/images/{image_id}.png)",
    )

    mime_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="image/png",
        doc="Image MIME type (image/png, image/jpeg, etc.)",
    )

    message_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Position in chat history for linking to specific AI message (0-indexed)",
    )

    main_concepts: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="Array of 2-3 main concept strings from curation",
    )

    branches: Mapped[list[dict]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        doc="Array of branch objects with id, label, description for exploration",
    )

    image_generation_prompt: Mapped[str] = mapped_column(
        String(4096),
        nullable=False,
        doc="Full prompt sent to Gemini for audit trail and regeneration",
    )

    # Relationships
    session = relationship("SessionModel", back_populates="images")
