"""
Course CRUD operations.

Provides Create, Read, Update, Delete operations for CourseModel
with course-specific query methods.

Dependencies: sqlalchemy, backend.boundary.db.models
System role: Course persistence operations
"""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.boundary.db.models.course_model import CourseModel
from backend.boundary.db.models.session_model import SessionModel
from backend.boundary.db.CRUD.base_crud import BaseCRUD


class CourseCRUD(BaseCRUD[CourseModel]):
    """
    CRUD operations for CourseModel.

    Extends BaseCRUD with course-specific queries including
    eager loading of related sessions.
    """

    def __init__(self) -> None:
        """Initialize CourseCRUD with CourseModel."""
        super().__init__(CourseModel)

    async def get_with_sessions(
        self,
        session: AsyncSession,
        id: UUID,
    ) -> CourseModel | None:
        """
        Retrieve course with eagerly loaded sessions.

        Args:
            session: Async database session
            id: Course UUID

        Returns:
            CourseModel with sessions loaded, None if not found
        """
        stmt = (
            select(CourseModel)
            .where(CourseModel.id == id)
            .options(selectinload(CourseModel.sessions))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_with_sessions(
        self,
        session: AsyncSession,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[CourseModel]:
        """
        Retrieve all courses with eagerly loaded sessions.

        Args:
            session: Async database session
            limit: Maximum number of courses to return
            offset: Number of courses to skip

        Returns:
            Sequence of CourseModels with sessions loaded
        """
        stmt = (
            select(CourseModel)
            .options(selectinload(CourseModel.sessions))
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_by_course_id(
        self,
        session: AsyncSession,
        course_id: UUID,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[SessionModel]:
        """
        Retrieve all sessions for a course.

        Args:
            session: Async database session
            course_id: Course UUID
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            Sequence of SessionModels for the course
        """
        stmt = (
            select(SessionModel)
            .where(SessionModel.course_id == course_id)
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()


course_crud = CourseCRUD()
