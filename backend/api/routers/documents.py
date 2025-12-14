"""
Document API endpoints.

Routes: POST /sessions/{id}/docs, GET /sessions/{id}/docs

Dependencies: backend.application.document_service, backend.models
System role: Document HTTP API
"""

from uuid import UUID
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_document_service, get_job_service
from backend.application.services.document_service import DocumentService
from backend.application.services.job_service import JobService
from backend.boundary.db import get_db
from backend.boundary.db.models.job_model import JobType, JobStatus
from backend.models.document import UploadDocumentsRequest, DocumentListResponse

router = APIRouter(prefix="/sessions", tags=["documents"])


async def process_document_background(
    job_id: UUID,
    file_path: str,
    session_id: UUID,
    document_name: str,
    db: AsyncSession,
) -> None:
    """
    Background task for document processing.

    Updates job status throughout the processing pipeline.

    Args:
        job_id: Job UUID for status tracking
        file_path: Path to uploaded document
        session_id: Session UUID
        document_name: Document filename
        db: Database session (created fresh for background task)
    """
    # Import here to avoid circular dependencies
    from backend.api.deps import get_document_service, get_job_service

    document_service = get_document_service(db=db)
    job_service = get_job_service(db=db)

    try:
        # Mark job as running
        await job_service.mark_job_running(job_id, progress=10)

        # Process document through pipeline
        result = await document_service.upload_document(
            file_path=file_path,
            session_id=session_id,
            document_name=document_name,
        )

        # Mark job as completed
        await job_service.mark_job_completed(
            job_id,
            result_data={
                "document_id": result.document_id,
                "chunk_count": result.chunk_count,
                "processing_time_ms": result.processing_time_ms,
                "index_path": result.index_path,
            },
        )

    except Exception as e:
        # Mark job as failed
        await job_service.mark_job_failed(
            job_id,
            error_details={
                "error": str(e),
                "type": type(e).__name__,
            },
        )


@router.post("/{session_id}/docs")
async def upload_documents(
    session_id: UUID,
    request: UploadDocumentsRequest,
    background_tasks: BackgroundTasks,
    job_service: JobService = Depends(get_job_service),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Upload documents to session (non-blocking).

    Creates job for background processing and returns job_id for polling.
    Frontend can poll /jobs/{job_id} for status updates.

    Args:
        session_id: Session UUID
        request: Upload request with file paths
        background_tasks: FastAPI background tasks
        job_service: Injected JobService
        db: Database session

    Returns:
        dict: Job ID and initial status for frontend polling

    Raises:
        HTTPException(400): Invalid request
    """
    if not request.files:
        raise HTTPException(status_code=400, detail="No files provided")

    # Create job for tracking
    task_id = str(uuid_lib.uuid4())
    job_id = await job_service.create_job(
        job_type=JobType.DOCUMENT_INGESTION,
        task_id=task_id,
    )

    # Process first file (for now, single file upload)
    # TODO: Support multiple files with separate jobs
    file_path = request.files[0]
    document_name = file_path.split("/")[-1]

    # Add background task for processing
    background_tasks.add_task(
        process_document_background,
        job_id=job_id,
        file_path=file_path,
        session_id=session_id,
        document_name=document_name,
        db=db,
    )

    return {
        "job_id": str(job_id),
        "status": JobStatus.PENDING.value,
        "message": "Document upload started. Poll /jobs/{job_id} for status.",
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
    """
    result = await document_service.get_documents(
        session_id=session_id,
        cursor=cursor,
    )

    # Map to response model
    from backend.models.document import DocumentResponse

    documents = [
        DocumentResponse(
            id=UUID(doc["id"]),
            session_id=session_id,
            name=doc["name"],
            status=doc["status"],
            created_at=doc["created_at"],
            error_message=doc.get("error_message"),
        )
        for doc in result["documents"]
    ]

    return DocumentListResponse(
        documents=documents,
        total=result["total"],
        cursor=result.get("cursor"),
    )
