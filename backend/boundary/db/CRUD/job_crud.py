"""
Job CRUD operations.

Provides Create, Read, Update, Delete operations for JobModel
with job-specific query methods for status tracking and SQS correlation.

Dependencies: sqlalchemy, backend.boundary.db.job_model
System role: Job persistence operations for async task tracking
"""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.job_model import JobModel, JobStatus, JobType
from backend.boundary.db.CRUD.base_crud import BaseCRUD


class JobCRUD(BaseCRUD[JobModel]):
    """
    CRUD operations for JobModel.

    Extends BaseCRUD with job-specific queries for task correlation,
    status tracking, and progress reporting.
    """

    def __init__(self) -> None:
        """Initialize JobCRUD with JobModel."""
        super().__init__(JobModel)

    async def get_by_task_id(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> JobModel | None:
        """
        Retrieve job by SQS message ID.

        Args:
            session: Async database session
            task_id: SQS MessageId for Lambda correlation

        Returns:
            JobModel if found, None otherwise
        """
        stmt = select(JobModel).where(JobModel.task_id == task_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_status(
        self,
        session: AsyncSession,
        status: JobStatus,
        limit: int | None = None,
    ) -> Sequence[JobModel]:
        """
        Retrieve jobs by execution status.

        Args:
            session: Async database session
            status: Job execution status to filter by
            limit: Maximum number of jobs to return

        Returns:
            Sequence of JobModels with matching status
        """
        stmt = select(JobModel).where(JobModel.status == status)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_by_type(
        self,
        session: AsyncSession,
        job_type: JobType,
        limit: int | None = None,
    ) -> Sequence[JobModel]:
        """
        Retrieve jobs by type.

        Args:
            session: Async database session
            job_type: Job classification type to filter by
            limit: Maximum number of jobs to return

        Returns:
            Sequence of JobModels with matching type
        """
        stmt = select(JobModel).where(JobModel.type == job_type)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self,
        session: AsyncSession,
        id: UUID,
        status: JobStatus,
        progress: int | None = None,
        result_data: dict | None = None,
    ) -> JobModel | None:
        """
        Update job execution status with optional progress and result.

        Args:
            session: Async database session
            id: Job UUID
            status: New execution status
            progress: Progress percentage (0-100)
            result_data: Job result or error details

        Returns:
            Updated JobModel if found, None otherwise
        """
        update_fields: dict = {"status": status}
        if progress is not None:
            update_fields["progress"] = progress
        if result_data is not None:
            update_fields["result"] = result_data
        return await self.update_by_id(session, id, **update_fields)

    async def update_progress(
        self,
        session: AsyncSession,
        id: UUID,
        progress: int,
    ) -> JobModel | None:
        """
        Update job progress percentage.

        Args:
            session: Async database session
            id: Job UUID
            progress: Progress percentage (0-100)

        Returns:
            Updated JobModel if found, None otherwise
        """
        return await self.update_by_id(session, id, progress=progress)

    async def mark_running(
        self,
        session: AsyncSession,
        id: UUID,
        progress: int = 0,
    ) -> JobModel | None:
        """
        Mark job as running.

        Args:
            session: Async database session
            id: Job UUID
            progress: Initial progress percentage

        Returns:
            Updated JobModel if found, None otherwise
        """
        return await self.update_status(session, id, JobStatus.RUNNING, progress)

    async def mark_completed(
        self,
        session: AsyncSession,
        id: UUID,
        result_data: dict,
    ) -> JobModel | None:
        """
        Mark job as successfully completed with result.

        Args:
            session: Async database session
            id: Job UUID
            result_data: Job output data

        Returns:
            Updated JobModel if found, None otherwise
        """
        return await self.update_status(
            session, id, JobStatus.COMPLETED, progress=100, result_data=result_data
        )

    async def mark_failed(
        self,
        session: AsyncSession,
        id: UUID,
        error_details: dict,
    ) -> JobModel | None:
        """
        Mark job as failed with error details.

        Args:
            session: Async database session
            id: Job UUID
            error_details: Error information dict

        Returns:
            Updated JobModel if found, None otherwise
        """
        return await self.update_status(
            session, id, JobStatus.FAILED, result_data=error_details
        )


job_crud = JobCRUD()
