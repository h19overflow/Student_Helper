"""
Course ORM model.

Represents a course container for organizing related study sessions.
Courses provide higher-level organization with session grouping.

Dependencies: sqlalchemy, backend.boundary.db.base
System role: Course persistence for session organization
"""

from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.boundary.db.base import Base, UUIDMixin, TimestampMixin


class CourseModel(Base, UUIDMixin, TimestampMixin):
    """
    Course ORM model for organizing sessions.

    A course acts as a container for multiple related study sessions.
    Sessions can optionally belong to a course. Deleting a course
    does not delete its sessions (ON DELETE SET NULL).

    Attributes:
        id: UUID primary key (auto-generated)
        name: Course name (255 char limit)
        description: Optional course description (up to 4096 chars)
        course_metadata: JSONB field storing course-specific data
        sessions: List of SessionModel rows for this course
        created_at: Course creation timestamp (UTC)
        updated_at: Last modification timestamp (UTC)

    Relationships:
        sessions: One-to-many with SessionModel (SET NULL on course deletion)
    """

    __tablename__ = "courses"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Course name"
    )

    description: Mapped[str | None] = mapped_column(
        String(4096),
        nullable=True,
        default=None,
        doc="Course description"
    )

    course_metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        doc="Course metadata (tags, difficulty, prerequisites, etc.)"
    )

    # Relationships
    sessions = relationship(
        "SessionModel",
        back_populates="course",
        foreign_keys="SessionModel.course_id"
    )
