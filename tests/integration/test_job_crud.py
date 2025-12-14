"""
Test suite for JobCRUD database operations.

Tests job-specific CRUD methods including filtering by task ID, status, type,
and progress tracking. Uses async fixtures with SQLAlchemy mocking.

System role: Verification of job persistence layer for async task tracking
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.CRUD.job_crud import JobCRUD
from backend.boundary.db.models.job_model import JobModel, JobStatus, JobType


@pytest.fixture
def job_crud() -> JobCRUD:
    """Provide JobCRUD instance for testing."""
    return JobCRUD()


@pytest.fixture
def mock_session() -> AsyncSession:
    """Provide mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_id() -> uuid.UUID:
    """Provide sample UUID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_task_id() -> str:
    """Provide sample SQS task ID for testing."""
    return "MessageId-12345-67890"


@pytest.fixture
def mock_job_model(sample_id: uuid.UUID, sample_task_id: str) -> JobModel:
    """Provide mock JobModel instance."""
    job = JobModel()
    job.id = sample_id
    job.task_id = sample_task_id
    job.type = JobType.DOCUMENT_INGESTION
    job.status = JobStatus.PENDING
    job.progress = 0
    job.result = {}
    job.created_at = datetime.now(timezone.utc)
    job.updated_at = datetime.now(timezone.utc)
    return job


class TestJobCRUDInit:
    """Test suite for JobCRUD initialization."""

    def test_init_should_set_model_to_job_model(self) -> None:
        """Test JobCRUD initializes with JobModel."""
        # Act
        crud = JobCRUD()

        # Assert
        assert crud.model == JobModel


class TestJobCRUDGetByTaskID:
    """Test suite for JobCRUD.get_by_task_id() method."""

    @pytest.mark.asyncio
    async def test_get_by_task_id_should_return_job_when_found(
        self,
        job_crud: JobCRUD,
        mock_session: AsyncSession,
        sample_task_id: str,
        mock_job_model: JobModel,
    ) -> None:
        """Test get_by_task_id returns job when task ID exists."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_job_model)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.get_by_task_id(mock_session, sample_task_id)

        # Assert
        assert result == mock_job_model
        assert result.task_id == sample_task_id

    @pytest.mark.asyncio
    async def test_get_by_task_id_should_return_none_when_not_found(
        self, job_crud: JobCRUD, mock_session: AsyncSession, sample_task_id: str
    ) -> None:
        """Test get_by_task_id returns None when task ID doesn't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.get_by_task_id(mock_session, sample_task_id)

        # Assert
        assert result is None


class TestJobCRUDGetByStatus:
    """Test suite for JobCRUD.get_by_status() method."""

    @pytest.mark.asyncio
    async def test_get_by_status_should_return_jobs_with_status(
        self,
        job_crud: JobCRUD,
        mock_session: AsyncSession,
        mock_job_model: JobModel,
    ) -> None:
        """Test get_by_status returns jobs with specific status."""
        # Arrange
        jobs = [mock_job_model]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=jobs)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.get_by_status(mock_session, JobStatus.PENDING)

        # Assert
        assert result == jobs
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_status_should_return_empty_when_no_jobs(
        self, job_crud: JobCRUD, mock_session: AsyncSession
    ) -> None:
        """Test get_by_status returns empty when no jobs match status."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.get_by_status(mock_session, JobStatus.RUNNING)

        # Assert
        assert result == []


class TestJobCRUDGetByType:
    """Test suite for JobCRUD.get_by_type() method."""

    @pytest.mark.asyncio
    async def test_get_by_type_should_return_jobs_with_type(
        self,
        job_crud: JobCRUD,
        mock_session: AsyncSession,
        mock_job_model: JobModel,
    ) -> None:
        """Test get_by_type returns jobs with specific type."""
        # Arrange
        jobs = [mock_job_model]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=jobs)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.get_by_type(
            mock_session, JobType.DOCUMENT_INGESTION
        )

        # Assert
        assert result == jobs
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_by_type_should_return_empty_when_no_jobs(
        self, job_crud: JobCRUD, mock_session: AsyncSession
    ) -> None:
        """Test get_by_type returns empty when no jobs match type."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.get_by_type(mock_session, JobType.EVALUATION)

        # Assert
        assert result == []


class TestJobCRUDUpdateStatus:
    """Test suite for JobCRUD.update_status() method."""

    @pytest.mark.asyncio
    async def test_update_status_should_return_updated_job(
        self,
        job_crud: JobCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_job_model: JobModel,
    ) -> None:
        """Test update_status returns updated job model."""
        # Arrange
        updated_job = mock_job_model
        updated_job.status = JobStatus.RUNNING

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_job)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.update_status(
            mock_session, sample_id, JobStatus.RUNNING
        )

        # Assert
        assert result == updated_job
        assert result.status == JobStatus.RUNNING

    @pytest.mark.asyncio
    async def test_update_status_should_return_none_when_not_found(
        self,
        job_crud: JobCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
    ) -> None:
        """Test update_status returns None when job doesn't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.update_status(
            mock_session, sample_id, JobStatus.RUNNING
        )

        # Assert
        assert result is None


class TestJobCRUDUpdateProgress:
    """Test suite for JobCRUD.update_progress() method."""

    @pytest.mark.asyncio
    async def test_update_progress_should_return_updated_job(
        self,
        job_crud: JobCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_job_model: JobModel,
    ) -> None:
        """Test update_progress returns job with updated progress."""
        # Arrange
        updated_job = mock_job_model
        updated_job.progress = 75

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_job)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.update_progress(mock_session, sample_id, 75)

        # Assert
        assert result == updated_job
        assert result.progress == 75


class TestJobCRUDMarkRunning:
    """Test suite for JobCRUD.mark_running() method."""

    @pytest.mark.asyncio
    async def test_mark_running_should_set_status_to_running(
        self,
        job_crud: JobCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_job_model: JobModel,
    ) -> None:
        """Test mark_running sets status to RUNNING."""
        # Arrange
        updated_job = mock_job_model
        updated_job.status = JobStatus.RUNNING

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_job)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.mark_running(mock_session, sample_id)

        # Assert
        assert result == updated_job
        assert result.status == JobStatus.RUNNING


class TestJobCRUDMarkCompleted:
    """Test suite for JobCRUD.mark_completed() method."""

    @pytest.mark.asyncio
    async def test_mark_completed_should_set_status_and_result(
        self,
        job_crud: JobCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_job_model: JobModel,
    ) -> None:
        """Test mark_completed sets status to COMPLETED and 100% progress."""
        # Arrange
        result_data = {"success": True}
        updated_job = mock_job_model
        updated_job.status = JobStatus.COMPLETED
        updated_job.progress = 100
        updated_job.result = result_data

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_job)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.mark_completed(mock_session, sample_id, result_data)

        # Assert
        assert result == updated_job
        assert result.status == JobStatus.COMPLETED
        assert result.progress == 100
        assert result.result == result_data


class TestJobCRUDMarkFailed:
    """Test suite for JobCRUD.mark_failed() method."""

    @pytest.mark.asyncio
    async def test_mark_failed_should_set_status_and_error_details(
        self,
        job_crud: JobCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
        mock_job_model: JobModel,
    ) -> None:
        """Test mark_failed sets status to FAILED and includes error details."""
        # Arrange
        error_details = {"error": "timeout", "retry_count": 3}
        updated_job = mock_job_model
        updated_job.status = JobStatus.FAILED
        updated_job.result = error_details

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_job)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.mark_failed(mock_session, sample_id, error_details)

        # Assert
        assert result == updated_job
        assert result.status == JobStatus.FAILED
        assert result.result == error_details


class TestJobCRUDInheritance:
    """Test suite for JobCRUD inheritance from BaseCRUD."""

    @pytest.mark.asyncio
    async def test_inherited_get_by_id_method_should_work(
        self,
        job_crud: JobCRUD,
        mock_session: AsyncSession,
        sample_id: uuid.UUID,
    ) -> None:
        """Test JobCRUD inherits get_by_id method from BaseCRUD."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await job_crud.get_by_id(mock_session, sample_id)

        # Assert
        assert result is None
