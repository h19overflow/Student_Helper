"""
Job service orchestrator.

Coordinates job tracking and status reporting for background tasks.
Wraps JobCRUD for job lifecycle management.

Dependencies: backend.boundary.db.CRUD, backend.boundary.db.models
System role: Job management orchestration
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.CRUD.job_crud import job_crud
from backend.boundary.db.models.job_model import JobModel, JobStatus, JobType


class JobService:
    """
    Job service orchestrator.

    Manages job lifecycle for background tasks with status tracking.
    Provides abstraction over JobCRUD for job operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize job service.

        Args:
            db: AsyncSession for database operations
        """
        self.db = db

    async def create_job(
        self,
        job_type: JobType,
        task_id: str,
    ) -> UUID:
        """
        Create new job record for background task tracking.

        Args:
            job_type: Type of job (DOCUMENT_INGESTION, EVALUATION)
            task_id: Unique task identifier (can be UUID string)

        Returns:
            UUID: Created job ID
        """
        job = await job_crud.create(
            self.db,
            task_id=task_id,
            type=job_type,
            status=JobStatus.PENDING,
            progress=0,
            result={},
        )
        return job.id

    async def update_job_status(
        self,
        job_id: UUID,
        status: JobStatus,
        progress: int | None = None,
        result_data: dict | None = None,
    ) -> None:
        """
        Update job status with optional progress and result data.

        Args:
            job_id: Job UUID
            status: New job status
            progress: Progress percentage (0-100)
            result_data: Job result or error details
        """
        await job_crud.update_status(
            self.db,
            job_id,
            status,
            progress,
            result_data,
        )

    async def mark_job_running(self, job_id: UUID, progress: int = 0) -> None:
        """
        Mark job as running.

        Args:
            job_id: Job UUID
            progress: Initial progress percentage
        """
        await job_crud.mark_running(self.db, job_id, progress)

    async def mark_job_completed(
        self,
        job_id: UUID,
        result_data: dict,
    ) -> None:
        """
        Mark job as successfully completed.

        Args:
            job_id: Job UUID
            result_data: Job result data
        """
        await job_crud.mark_completed(self.db, job_id, result_data)

    async def mark_job_failed(
        self,
        job_id: UUID,
        error_details: dict,
    ) -> None:
        """
        Mark job as failed with error details.

        Args:
            job_id: Job UUID
            error_details: Error information
        """
        await job_crud.mark_failed(self.db, job_id, error_details)

    async def get_job_status(self, job_id: UUID) -> dict:
        """
        Get job status details for polling.

        Args:
            job_id: Job UUID

        Returns:
            dict: Job status information

        Raises:
            ValueError: If job doesn't exist
        """
        job = await job_crud.get_by_id(self.db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} does not exist")

        return {
            "id": str(job.id),
            "task_id": job.task_id,
            "type": job.type.value,
            "status": job.status.value,
            "progress": job.progress,
            "result": job.result,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
        }
