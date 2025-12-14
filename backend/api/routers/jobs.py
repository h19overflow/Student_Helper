"""
Job API endpoints.

Routes: GET /jobs/{id}

Dependencies: backend.application.job_service, backend.models
System role: Job status HTTP API
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_job_service
from backend.application.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job_status(
    job_id: UUID,
    job_service: JobService = Depends(get_job_service),
) -> dict:
    """
    Get job status and progress for frontend polling.

    Returns current job status, progress percentage, and result data.
    Frontend should poll this endpoint every 1-2 seconds while job is PENDING or RUNNING.

    Args:
        job_id: Job UUID
        job_service: Injected JobService

    Returns:
        dict: Job status information with:
            - id: Job UUID
            - task_id: Unique task identifier
            - type: Job type (DOCUMENT_INGESTION, EVALUATION)
            - status: Current status (PENDING, RUNNING, COMPLETED, FAILED)
            - progress: Progress percentage (0-100)
            - result: Job result or error details
            - created_at: Job creation timestamp
            - updated_at: Last update timestamp

    Raises:
        HTTPException(404): Job not found

    Example Response:
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "task_id": "task-abc123",
            "type": "document_ingestion",
            "status": "completed",
            "progress": 100,
            "result": {
                "document_id": "doc-123",
                "chunk_count": 42,
                "processing_time_ms": 1234.56
            },
            "created_at": "2025-01-01T12:00:00",
            "updated_at": "2025-01-01T12:00:05"
        }
    """
    try:
        status = await job_service.get_job_status(job_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
