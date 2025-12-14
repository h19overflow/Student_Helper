"""
SQLAlchemy declarative base and common mixins.

Provides base class for all ORM models and reusable mixins
for common fields (timestamps, UUIDs).

Dependencies: sqlalchemy
System role: Foundation for all database models
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base for ORM model registration.

    All database models inherit from this class to ensure they're
    registered with the metadata and included in table creation.
    """

    pass


class UUIDMixin:
    """
    Mixin providing UUID primary key to all models.

    Generates UUID v4 automatically on row creation. PostgreSQL stores
    as native UUID type for efficient indexing and sorting.

    Attributes:
        id: UUID v4 primary key, auto-generated on insert
    """

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class TimestampMixin:
    """
    Mixin providing automatic timestamp tracking to all models.

    created_at is set once on row creation and never changes.
    updated_at is refreshed on every update via onupdate hook.
    Both use UTC timezone for consistency across deployments.

    Attributes:
        created_at: Row creation timestamp (UTC, immutable)
        updated_at: Last modification timestamp (UTC, auto-updated)
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
