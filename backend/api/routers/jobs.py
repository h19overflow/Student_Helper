"""
Job API endpoints.

Routes: GET /jobs/{id}

Dependencies: backend.application.job_service, backend.models
System role: Job status HTTP API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import uuid

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job_status(job_id: uuid.UUID, db: Session = Depends()):
    """Get job status and progress."""
    pass
