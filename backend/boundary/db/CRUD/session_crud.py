"""
Session CRUD operations.

Provides Create, Read, Update, Delete operations for SessionModel
with session-specific query methods.

Dependencies: sqlalchemy, backend.boundary.db.session_model
System role: Session persistence operations
"""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.boundary.db.session_model import SessionModel
from backend.boundary.db.CRUD.base_crud import BaseCRUD


class SessionCRUD(BaseCRUD[SessionModel]):
    """
    CRUD operations for SessionModel.

    Extends BaseCRUD with session-specific queries including
    eager loading of related documents.
    """

    def __init__(self) -> None:
        """Initialize SessionCRUD with SessionModel."""
        super().__init__(SessionModel)

    async def get_with_documents(
        self,
        session: AsyncSession,
        id: UUID,
    ) -> SessionModel | None:
        """
        Retrieve session with eagerly loaded documents.

        Args:
            session: Async database session
            id: Session UUID

        Returns:
            SessionModel with documents loaded, None if not found
        """
        stmt = (
            select(SessionModel)
            .where(SessionModel.id == id)
            .options(selectinload(SessionModel.documents))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_with_documents(
        self,
        session: AsyncSession,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[SessionModel]:
        """
        Retrieve all sessions with eagerly loaded documents.

        Args:
            session: Async database session
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            Sequence of SessionModels with documents loaded
        """
        stmt = (
            select(SessionModel)
            .options(selectinload(SessionModel.documents))
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update_metadata(
        self,
        session: AsyncSession,
        id: UUID,
        metadata: dict,
    ) -> SessionModel | None:
        """
        Update session metadata.

        Args:
            session: Async database session
            id: Session UUID
            metadata: New metadata dict to replace existing

        Returns:
            Updated SessionModel if found, None otherwise
        """
        return await self.update_by_id(session, id, session_metadata=metadata)


session_crud = SessionCRUD()
