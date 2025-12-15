"""
Document API endpoints.

Routes: POST /sessions/{id}/docs, GET /sessions/{id}/docs

Dependencies: backend.application.document_service, backend.models
System role: Document HTTP API
"""

import logging
import shutil
import tempfile
from pathlib import Path
from uuid import UUID
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File

logger = logging.getLogger(__name__)

from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_document_service, get_job_service
from backend.api.routers.router_utils.document_utils import process_document_background
from backend.application.services.document_service import DocumentService
from backend.application.services.job_service import JobService
from backend.boundary.db.connection import get_async_db
from backend.boundary.db.models.job_model import JobType, JobStatus
from backend.models.document import DocumentListResponse

router = APIRouter(prefix="/sessions", tags=["documents"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB


@router.post("/{session_id}/docs")
async def upload_documents(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Upload document to session via multipart form (non-blocking).

    Saves file to temp location, creates job for background processing,
    and returns job_id for polling. Temp file is cleaned up after processing.

    Args:
        session_id: Session UUID
        file: Uploaded file (multipart form)
        background_tasks: FastAPI background tasks
        job_service: Injected JobService
        db: Database session for explicit commit

    Returns:
        dict: Job ID and initial status for frontend polling

    Raises:
        HTTPException(400): Invalid file type or size
        HTTPException(500): File save failed
    """
    logger.info(
        "Document upload request received",
        extra={"session_id": str(session_id), "document_name": file.filename},
    )

    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        logger.warning(
            "Upload rejected: invalid file type",
            extra={"session_id": str(session_id), "document_name": file.filename, "extension": file_ext},
        )
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file_ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Save file to temp location
    try:
        # Create temp file with original extension
        temp_dir = tempfile.mkdtemp(prefix="studybuddy_")
        temp_path = Path(temp_dir) / file.filename

        # Read and save file content
        content = await file.read()

        # Validate file size
        if len(content) > MAX_FILE_SIZE:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        with open(temp_path, "wb") as f:
            f.write(content)

        logger.info(
            "File saved to temp location",
            extra={"session_id": str(session_id), "temp_path": str(temp_path), "size": len(content)},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Failed to save uploaded file",
            extra={"session_id": str(session_id), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

    # Create job for tracking
    task_id = str(uuid_lib.uuid4())
    job_id = await job_service.create_job(
        job_type=JobType.DOCUMENT_INGESTION,
        task_id=task_id,
    )

    # Commit job creation immediately so polling can find it
    await job_service.db.commit()

    logger.info(
        "Job created and committed",
        extra={"job_id": str(job_id), "task_id": task_id},
    )

    # Add background task for processing (includes cleanup)
    background_tasks.add_task(
        process_document_background,
        job_id=job_id,
        file_path=str(temp_path),
        session_id=session_id,
        document_name=file.filename,
    )

    return {
        "jobId": str(job_id),
        "status": JobStatus.PENDING.value,
        "message": "Document upload started. Poll /jobs/{jobId} for status.",
    }


@router.get("/{session_id}/docs", response_model=DocumentListResponse)
async def get_documents(
    session_id: UUID,
    cursor: str | None = None,
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """
    Get paginated document list for session.

    Args:
        session_id: Session UUID
        cursor: Optional pagination cursor
        document_service: Injected DocumentService

    Returns:
        DocumentListResponse: List of documents with metadata

    Raises:
        HTTPException(500): Database or service error
    """
    logger.info("Fetching documents for session", extra={"session_id": str(session_id)})

    try:
        documents_list = await document_service.get_session_documents(
            session_id=session_id,
        )

        # Map to response model
        from backend.models.document import DocumentResponse

        documents = [
            DocumentResponse(
                id=doc.id,
                session_id=doc.session_id,
                name=doc.name,
                status=doc.status.value if hasattr(doc.status, "value") else doc.status,
                created_at=doc.created_at,
                error_message=doc.error_message,
            )
            for doc in documents_list
        ]

        logger.info(
            "Documents fetched successfully",
            extra={"session_id": str(session_id), "document_count": len(documents)},
        )

        return DocumentListResponse(
            documents=documents,
            total=len(documents),
            cursor=None,
        )

    except Exception as e:
        logger.exception(
            "Failed to fetch documents",
            extra={"session_id": str(session_id), "error": str(e), "error_type": type(e).__name__},
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch documents: {str(e)}",
        )
