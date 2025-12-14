"""
Base CRUD operations for SQLAlchemy models.

Provides generic Create, Read, Update, Delete operations that can be
inherited and extended by model-specific CRUD classes.

Dependencies: sqlalchemy, uuid
System role: Foundation for all database CRUD operations
"""

from typing import Generic, TypeVar, Sequence
from uuid import UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseCRUD(Generic[ModelT]):
    """
    Generic base class for CRUD operations.

    Provides standard database operations that work with any SQLAlchemy model.
    Subclasses should specify the model class and can override or extend
    these methods for model-specific behavior.

    Type Parameters:
        ModelT: SQLAlchemy model class inheriting from Base

    Attributes:
        model: The SQLAlchemy model class to operate on
    """

    def __init__(self, model: type[ModelT]) -> None:
        """
        Initialize CRUD with target model.

        Args:
            model: SQLAlchemy model class for database operations
        """
        self.model = model

    async def create(self, session: AsyncSession, **kwargs) -> ModelT:
        """
        Create a new record in the database.

        Args:
            session: Async database session
            **kwargs: Model field values

        Returns:
            Created model instance with generated ID and timestamps
        """
        instance = self.model(**kwargs)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    async def get_by_id(self, session: AsyncSession, id: UUID) -> ModelT | None:
        """
        Retrieve a single record by primary key.

        Args:
            session: Async database session
            id: UUID primary key

        Returns:
            Model instance if found, None otherwise
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        session: AsyncSession,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[ModelT]:
        """
        Retrieve all records with optional pagination.

        Args:
            session: Async database session
            limit: Maximum number of records to return (None for all)
            offset: Number of records to skip

        Returns:
            Sequence of model instances
        """
        stmt = select(self.model).offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update_by_id(
        self,
        session: AsyncSession,
        id: UUID,
        **kwargs,
    ) -> ModelT | None:
        """
        Update a record by primary key.

        Args:
            session: Async database session
            id: UUID primary key
            **kwargs: Fields to update with new values

        Returns:
            Updated model instance if found, None otherwise
        """
        stmt = (
            update(self.model)
            .where(self.model.id == id)
            .values(**kwargs)
            .returning(self.model)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_id(self, session: AsyncSession, id: UUID) -> bool:
        """
        Delete a record by primary key.

        Args:
            session: Async database session
            id: UUID primary key

        Returns:
            True if record was deleted, False if not found
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await session.execute(stmt)
        return result.rowcount > 0

    async def exists(self, session: AsyncSession, id: UUID) -> bool:
        """
        Check if a record exists by primary key.

        Args:
            session: Async database session
            id: UUID primary key

        Returns:
            True if record exists, False otherwise
        """
        stmt = select(self.model.id).where(self.model.id == id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None
