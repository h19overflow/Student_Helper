"""
Document status updater for RDS.

Updates document processing status in PostgreSQL:
PENDING → PROCESSING → COMPLETED (or FAILED with error message)

Dependencies: sqlalchemy, backend.boundary.db.models
System role: Database persistence layer
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.models.document_model import DocumentModel, DocumentStatus

logger = logging.getLogger(__name__)


class DocumentStatusUpdater:
    """Update document status in RDS during processing."""

    def __init__(self, db_session: AsyncSession) -> None:
        """
        Initialize with database session.

        Args:
            db_session: AsyncSession for RDS
        """
        self.db = db_session

    async def mark_processing(self, document_id: str) -> None:
        """
        Mark document as PROCESSING.

        Called when Lambda receives SQS message and starts pipeline.

        Args:
            document_id: Document UUID

        Raises:
            ValueError: Document not found
        """
        try:
            stmt = select(DocumentModel).where(DocumentModel.id == document_id)
            result = await self.db.execute(stmt)
            document = result.scalar_one_or_none()

            if not document:
                raise ValueError(f"Document {document_id} not found")

            document.status = DocumentStatus.PROCESSING
            await self.db.commit()

            logger.info(
                f"{__name__}:mark_processing - Document marked as PROCESSING",
                extra={"document_id": document_id},
            )

        except Exception as e:
            logger.error(f"{__name__}:mark_processing - {type(e).__name__}: {e}")
            await self.db.rollback()
            raise

    async def mark_completed(self, document_id: str) -> None:
        """
        Mark document as COMPLETED.

        Called when pipeline successfully processes document.

        Args:
            document_id: Document UUID

        Raises:
            ValueError: Document not found
        """
        try:
            stmt = select(DocumentModel).where(DocumentModel.id == document_id)
            result = await self.db.execute(stmt)
            document = result.scalar_one_or_none()

            if not document:
                raise ValueError(f"Document {document_id} not found")

            document.status = DocumentStatus.COMPLETED
            document.error_message = None
            await self.db.commit()

            logger.info(
                f"{__name__}:mark_completed - Document marked as COMPLETED",
                extra={"document_id": document_id},
            )

        except Exception as e:
            logger.error(f"{__name__}:mark_completed - {type(e).__name__}: {e}")
            await self.db.rollback()
            raise

    async def mark_failed(self, document_id: str, error_message: str) -> None:
        """
        Mark document as FAILED with error details.

        Called when pipeline raises exception.

        Args:
            document_id: Document UUID
            error_message: Human-readable error description

        Raises:
            ValueError: Document not found
        """
        try:
            stmt = select(DocumentModel).where(DocumentModel.id == document_id)
            result = await self.db.execute(stmt)
            document = result.scalar_one_or_none()

            if not document:
                raise ValueError(f"Document {document_id} not found")

            document.status = DocumentStatus.FAILED
            document.error_message = error_message

            await self.db.commit()

            logger.info(
                f"{__name__}:mark_failed - Document marked as FAILED",
                extra={"document_id": document_id, "error_message": error_message},
            )

        except Exception as e:
            logger.error(f"{__name__}:mark_failed - {type(e).__name__}: {e}")
            await self.db.rollback()
            raise
