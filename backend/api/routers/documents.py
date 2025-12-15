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
from backend.application.services.document_service import DocumentService
from backend.application.services.job_service import JobService
from backend.boundary.db.connection import get_async_db
from backend.boundary.db.models.job_model import JobType, JobStatus
from backend.boundary.vdb.dev_task import DevDocumentPipeline
from backend.models.document import UploadDocumentsRequest, DocumentListResponse

router = APIRouter(prefix="/sessions", tags=["documents"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {".pdf"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB


def cleanup_temp_file(file_path: str) -> None:
    """
    Safely remove temporary file and its parent temp directory.

    Args:
        file_path: Path to file to remove
    """
    try:
        path = Path(file_path)
        parent_dir = path.parent

        # Remove the file
        if path.exists():
            path.unlink()
            logger.debug("Cleaned up temp file", extra={"file_path": file_path})

        # Remove the temp directory if it's a studybuddy temp dir and empty
        if parent_dir.exists() and parent_dir.name.startswith("studybuddy_"):
            shutil.rmtree(parent_dir, ignore_errors=True)
            logger.debug("Cleaned up temp directory", extra={"temp_dir": str(parent_dir)})

    except Exception as e:
        logger.warning(
            "Failed to cleanup temp file",
            extra={"file_path": file_path, "error": str(e)},
        )


async def process_document_background(
    job_id: UUID,
    file_path: str,
    session_id: UUID,
    document_name: str,
) -> None:
    """
    Background task for document processing.

    Creates its own async database session for the background context.
    Always cleans up the temp file after processing (success or failure).

    Args:
        job_id: Job UUID for status tracking
        file_path: Path to uploaded document (temp file)
        session_id: Session UUID
        document_name: Document filename
    """
    from backend.boundary.db.connection import get_async_session_factory

    logger.info(
        "Starting background document processing",
        extra={
            "job_id": str(job_id),
            "session_id": str(session_id),
            "document_name": document_name,
            "file_path": file_path,
        },
    )

    # Create fresh async session for background task
    SessionFactory = get_async_session_factory()

    try:
        async with SessionFactory() as db:
            try:
                # Create services with fresh session
                dev_pipeline = DevDocumentPipeline(
                    chunk_size=1000,
                    chunk_overlap=200,
                    persist_directory=".faiss_index",
                )
                document_service = DocumentService(db=db, dev_pipeline=dev_pipeline)
                job_service = JobService(db=db)

                # Mark job as running
                logger.debug("Marking job as running", extra={"job_id": str(job_id)})
                await job_service.mark_job_running(job_id, progress=10)

                # Process document through pipeline
                logger.info(
                    "Processing document through pipeline",
                    extra={"job_id": str(job_id), "file_path": file_path},
                )
                result = await document_service.upload_document(
                    file_path=file_path,
                    session_id=session_id,
                    document_name=document_name,
                )

                # Mark job as completed
                result_data = {
                    "document_id": str(result.document_id) if hasattr(result, 'document_id') else None,
                    "chunk_count": result.chunk_count if hasattr(result, 'chunk_count') else 0,
                    "processing_time_ms": result.processing_time_ms if hasattr(result, 'processing_time_ms') else 0,
                    "index_path": result.index_path if hasattr(result, 'index_path') else None,
                }
                logger.info(
                    "Document processing completed",
                    extra={"job_id": str(job_id), "result": result_data},
                )
                await job_service.mark_job_completed(job_id, result_data=result_data)
                await db.commit()

            except Exception as e:
                logger.exception(
                    "Document processing failed",
                    extra={
                        "job_id": str(job_id),
                        "session_id": str(session_id),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
                await db.rollback()
                # Mark job as failed
                try:
                    await job_service.mark_job_failed(
                        job_id,
                        error_details={
                            "error": str(e),
                            "type": type(e).__name__,
                        },
                    )
                    await db.commit()
                except Exception as inner_e:
                    logger.exception(
                        "Failed to record job failure",
                        extra={"job_id": str(job_id), "inner_error": str(inner_e)},
                    )
    finally:
        # Always cleanup temp file
        cleanup_temp_file(file_path)


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
