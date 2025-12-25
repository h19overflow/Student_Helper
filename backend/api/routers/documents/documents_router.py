"""
Document API endpoints.

Routes:
- POST /sessions/{id}/docs/presigned-url - Generate presigned URL for S3 upload
- POST /sessions/{id}/docs/uploaded - Notify upload completion
- DELETE /sessions/{id}/docs/{doc_id} - Delete document
- GET /sessions/{id}/docs - List session documents

Dependencies: backend.application.services, backend.models
System role: Document HTTP API
"""

import logging
from uuid import UUID
import uuid as uuid_lib

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_document_service, get_job_service, get_s3_document_client
from backend.application.services.document_service import DocumentService
from backend.application.services.job_service import JobService
from backend.boundary.aws.s3_client import S3DocumentClient
from backend.boundary.db.models.job_model import JobType, JobStatus
from backend.models.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadedNotification,
    PresignedUrlRequest,
    PresignedUrlResponse,
)

from .presigned_url_handler import (
    FilenameError,
    S3PresignError,
    handle_presigned_url_request,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["documents"])


@router.post("/{session_id}/docs/presigned-url", response_model=PresignedUrlResponse)
async def create_presigned_upload_url(
    session_id: UUID,
    request: PresignedUrlRequest,
    s3_client: S3DocumentClient = Depends(get_s3_document_client),
) -> PresignedUrlResponse:
    """
    Generate presigned URL for direct S3 upload.

    Frontend uses this URL to upload file directly to S3, bypassing the backend.
    After successful upload, frontend must call POST /docs/uploaded with the s3_key.

    Args:
        session_id: Session UUID
        request: Filename and content type
        s3_client: Injected S3 client

    Returns:
        PresignedUrlResponse: Presigned URL, s3_key, and expiry

    Raises:
        HTTPException(400): Invalid filename or extension
        HTTPException(500): Failed to generate URL
    """
    try:
        return handle_presigned_url_request(session_id, request, s3_client)
    except FilenameError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except S3PresignError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{session_id}/docs/uploaded")
async def document_uploaded_to_s3(
    session_id: UUID,
    notification: DocumentUploadedNotification,
    job_service: JobService = Depends(get_job_service),
) -> dict:
    """
    Handle notification that document was uploaded to S3.

    Called by frontend after successful upload to S3 using presigned URL.
    Creates a job and queues background processing.

    Args:
        session_id: Session UUID
        notification: S3 key and filename from frontend
        job_service: Injected JobService

    Returns:
        dict: Job ID and status for polling

    Raises:
        HTTPException(500): Failed to create job
    """
    logger.info(
        "Document upload notification received",
        extra={
            "session_id": str(session_id),
            "s3_key": notification.s3_key,
            "file_name": notification.filename,
        },
    )

    try:
        # Create job for tracking
        task_id = str(uuid_lib.uuid4())
        job_id = await job_service.create_job(
            job_type=JobType.DOCUMENT_INGESTION,
            task_id=task_id,
        )

        # Commit job creation immediately so polling can find it
        await job_service.db.commit()

        logger.info(
            "Job created for S3 document processing",
            extra={"job_id": str(job_id), "task_id": task_id, "s3_key": notification.s3_key},
        )

        # S3 event → SQS → Lambda handles processing automatically
        return {
            "jobId": str(job_id),
            "status": JobStatus.PENDING.value,
            "message": "Document queued for processing. Poll /jobs/{jobId} for status.",
        }

    except Exception as e:
        logger.exception(
            "Failed to process upload notification",
            extra={"session_id": str(session_id), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to process upload notification")


@router.delete("/{session_id}/docs/{doc_id}", status_code=204)
async def delete_document(
    session_id: UUID,
    doc_id: UUID,
    document_service: DocumentService = Depends(get_document_service),
) -> None:
    """
    Delete document from session.

    Removes document from both S3 Vectors and database.
    All chunks associated with the document are deleted from the vector store.

    Args:
        session_id: Session UUID
        doc_id: Document UUID to delete
        document_service: Injected DocumentService

    Returns:
        204 No Content on success

    Raises:
        HTTPException(404): Document not found or doesn't belong to session
        HTTPException(500): Deletion failed
    """
    logger.info(
        "Document deletion request",
        extra={"session_id": str(session_id), "doc_id": str(doc_id)},
    )

    try:
        await document_service.delete_document(
            doc_id=doc_id,
            session_id=session_id,
        )

        logger.info(
            "Document deleted successfully",
            extra={"session_id": str(session_id), "doc_id": str(doc_id)},
        )

    except ValueError as e:
        logger.warning(
            "Document deletion validation failed",
            extra={"session_id": str(session_id), "doc_id": str(doc_id), "error": str(e)},
        )
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(
            "Failed to delete document",
            extra={"session_id": str(session_id), "doc_id": str(doc_id), "error": str(e)},
        )
        raise HTTPException(status_code=500, detail="Failed to delete document")


@router.get("/{session_id}/docs", response_model=DocumentListResponse)
async def get_documents(
    session_id: UUID,
    _cursor: str | None = None,  # Reserved for future pagination
    document_service: DocumentService = Depends(get_document_service),
) -> DocumentListResponse:
    """
    Get paginated document list for session.

    Args:
        session_id: Session UUID
        _cursor: Optional pagination cursor (reserved for future use)
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
        documents = [
            DocumentResponse(
                id=UUID(str(doc.id)),
                session_id=UUID(str(doc.session_id)),
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
