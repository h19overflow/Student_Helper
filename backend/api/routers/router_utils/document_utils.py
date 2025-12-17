"""
Document router utility functions.

Contains background processing and cleanup helpers for document endpoints.
Dependencies: backend.application.services, backend.boundary.db
System role: Document processing utilities
"""

import logging
import shutil
from pathlib import Path
from uuid import UUID

logger = logging.getLogger(__name__)


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
    from backend.application.services.document_service import DocumentService
    from backend.application.services.job_service import JobService
    from backend.boundary.db.connection import get_async_session_factory
    from backend.core.document_processing.entrypoint import DocumentPipeline

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
                pipeline = DocumentPipeline()
                document_service = DocumentService(db=db, pipeline=pipeline)
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
                    "document_id": result.document_id,
                    "chunk_count": result.chunk_count,
                    "processing_time_ms": result.processing_time_ms,
                    "output_path": result.output_path,
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


async def process_document_from_s3_background(
    job_id: UUID,
    s3_key: str,
    session_id: UUID,
    document_name: str,
) -> None:
    """
    Background task for document processing from S3.

    Downloads from S3, processes through pipeline, and updates job status.
    The pipeline handles S3 download and temp file cleanup internally.

    Args:
        job_id: Job UUID for status tracking
        s3_key: S3 object key (path in bucket)
        session_id: Session UUID
        document_name: Document filename
    """
    from backend.application.services.document_service import DocumentService
    from backend.application.services.job_service import JobService
    from backend.boundary.db.connection import get_async_session_factory
    from backend.core.document_processing.entrypoint import DocumentPipeline

    logger.info(
        "Starting background document processing from S3",
        extra={
            "job_id": str(job_id),
            "session_id": str(session_id),
            "document_name": document_name,
            "s3_key": s3_key,
        },
    )

    # Create fresh async session for background task
    SessionFactory = get_async_session_factory()

    try:
        async with SessionFactory() as db:
            try:
                # Create services with fresh session
                pipeline = DocumentPipeline()
                document_service = DocumentService(db=db, pipeline=pipeline)
                job_service = JobService(db=db)

                # Mark job as running
                logger.debug("Marking job as running", extra={"job_id": str(job_id)})
                await job_service.mark_job_running(job_id, progress=10)

                # Process document through pipeline (from S3)
                logger.info(
                    "Processing document from S3 through pipeline",
                    extra={"job_id": str(job_id), "s3_key": s3_key},
                )
                result = await document_service.upload_document(
                    s3_key=s3_key,
                    session_id=session_id,
                    document_name=document_name,
                )

                # Mark job as completed
                result_data = {
                    "document_id": result.document_id,
                    "chunk_count": result.chunk_count,
                    "processing_time_ms": result.processing_time_ms,
                    "output_path": result.output_path,
                }
                logger.info(
                    "Document processing completed",
                    extra={"job_id": str(job_id), "result": result_data},
                )
                await job_service.mark_job_completed(job_id, result_data=result_data)
                await db.commit()

            except Exception as e:
                logger.exception(
                    "Document processing from S3 failed",
                    extra={
                        "job_id": str(job_id),
                        "session_id": str(session_id),
                        "s3_key": s3_key,
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
    except Exception as e:
        logger.exception(
            "Failed to create database session for background task",
            extra={"job_id": str(job_id), "error": str(e)},
        )
