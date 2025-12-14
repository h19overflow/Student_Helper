"""
Example usage of database CRUD operations.

Demonstrates common patterns for session, document, and job management
using the CRUD singletons with async database sessions.

Dependencies: backend.boundary.db
System role: Reference examples for database operations
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db import (
    # CRUD singletons - use these for database operations
    session_crud,
    document_crud,
    job_crud,
    # Enums for status values
    DocumentStatus,
    JobStatus,
    JobType,
)


# =============================================================================
# Session CRUD Examples
# =============================================================================


async def create_session(db: AsyncSession) -> UUID:
    """Create a new session with metadata."""
    session = await session_crud.create(
        db,
        session_metadata={"user": "student_123", "topic": "calculus"},
    )
    return session.id


async def get_session_with_docs(db: AsyncSession, session_id: UUID):
    """Retrieve session with all documents eagerly loaded."""
    session = await session_crud.get_with_documents(db, session_id)
    if session:
        print(f"Session {session.id} has {len(session.documents)} documents")
    return session


async def list_all_sessions(db: AsyncSession, page: int = 1, page_size: int = 10):
    """Paginated session listing."""
    offset = (page - 1) * page_size
    return await session_crud.get_all(db, limit=page_size, offset=offset)


async def update_session_metadata(db: AsyncSession, session_id: UUID):
    """Update session metadata."""
    return await session_crud.update_metadata(
        db,
        session_id,
        metadata={"user": "student_123", "topic": "calculus", "completed": True},
    )


async def delete_session(db: AsyncSession, session_id: UUID):
    """Delete session (cascades to documents)."""
    deleted = await session_crud.delete_by_id(db, session_id)
    print(f"Session deleted: {deleted}")
    return deleted


# =============================================================================
# Document CRUD Examples
# =============================================================================


async def upload_document(db: AsyncSession, session_id: UUID) -> UUID:
    """Create a document record for upload tracking."""
    doc = await document_crud.create(
        db,
        session_id=session_id,
        name="lecture_notes.pdf",
        upload_url="s3://bucket/docs/lecture_notes.pdf",
        status=DocumentStatus.PENDING,
    )
    return doc.id


async def get_session_documents(db: AsyncSession, session_id: UUID):
    """Get all documents for a session."""
    return await document_crud.get_by_session_id(db, session_id)


async def get_pending_documents(db: AsyncSession):
    """Get documents awaiting processing."""
    return await document_crud.get_by_status(db, DocumentStatus.PENDING)


async def mark_document_processing(db: AsyncSession, doc_id: UUID):
    """Update document status to processing."""
    return await document_crud.update_status(db, doc_id, DocumentStatus.PROCESSING)


async def mark_document_completed(db: AsyncSession, doc_id: UUID):
    """Mark document as successfully processed."""
    return await document_crud.mark_completed(db, doc_id)


async def mark_document_failed(db: AsyncSession, doc_id: UUID, error: str):
    """Mark document as failed with error message."""
    return await document_crud.mark_failed(db, doc_id, error)


# =============================================================================
# Job CRUD Examples
# =============================================================================


async def create_ingestion_job(db: AsyncSession, sqs_message_id: str) -> UUID:
    """Create a job record for SQS message tracking."""
    job = await job_crud.create(
        db,
        task_id=sqs_message_id,
        type=JobType.DOCUMENT_INGESTION,
        status=JobStatus.PENDING,
        progress=0,
        result={},
    )
    return job.id


async def get_job_by_sqs_id(db: AsyncSession, sqs_message_id: str):
    """Look up job by SQS message ID."""
    return await job_crud.get_by_task_id(db, sqs_message_id)


async def get_running_jobs(db: AsyncSession):
    """Get all currently running jobs."""
    return await job_crud.get_by_status(db, JobStatus.RUNNING)


async def get_ingestion_jobs(db: AsyncSession):
    """Get all document ingestion jobs."""
    return await job_crud.get_by_type(db, JobType.DOCUMENT_INGESTION)


async def start_job(db: AsyncSession, job_id: UUID):
    """Mark job as running."""
    return await job_crud.mark_running(db, job_id, progress=0)


async def update_job_progress(db: AsyncSession, job_id: UUID, progress: int):
    """Update job progress percentage."""
    return await job_crud.update_progress(db, job_id, progress)


async def complete_job(db: AsyncSession, job_id: UUID, result: dict):
    """Mark job as completed with result."""
    return await job_crud.mark_completed(db, job_id, result)


async def fail_job(db: AsyncSession, job_id: UUID, error: dict):
    """Mark job as failed with error details."""
    return await job_crud.mark_failed(db, job_id, error)

