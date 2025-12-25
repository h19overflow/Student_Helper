"""
Database status management utilities for Lambda.
"""

import logging
from backend.core.document_processing.database.document_status_updater import DocumentStatusUpdater, get_async_session_factory

logger = logging.getLogger(__name__)


async def create_document_record(
    document_id: str, session_id: str, name: str, s3_key: str
) -> None:
    """Create document record in RDS."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        updater = DocumentStatusUpdater(session)
        await updater.create_document(document_id, session_id, name, s3_key)


async def update_status_processing(document_id: str) -> None:
    """Update document status to PROCESSING in RDS."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        updater = DocumentStatusUpdater(session)
        await updater.mark_processing(document_id)


async def update_status_completed(document_id: str) -> None:
    """Update document status to COMPLETED in RDS."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        updater = DocumentStatusUpdater(session)
        await updater.mark_completed(document_id)


async def update_status_failed(document_id: str, error_message: str) -> None:
    """Update document status to FAILED in RDS."""
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        updater = DocumentStatusUpdater(session)
        await updater.mark_failed(document_id, error_message)
