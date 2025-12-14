"""
Document CRUD operations.

Provides Create, Read, Update, Delete operations for DocumentModel
with document-specific query methods for status tracking and session filtering.

Dependencies: sqlalchemy, backend.boundary.db.document_model
System role: Document persistence operations
"""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.models.document_model import DocumentModel, DocumentStatus
from backend.boundary.db.CRUD.base_crud import BaseCRUD


class DocumentCRUD(BaseCRUD[DocumentModel]):
    """
    CRUD operations for DocumentModel.

    Extends BaseCRUD with document-specific queries for filtering
    by session and processing status.
    """

    def __init__(self) -> None:
        """Initialize DocumentCRUD with DocumentModel."""
        super().__init__(DocumentModel)

    async def get_by_session_id(
        self,
        session: AsyncSession,
        session_id: UUID,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[DocumentModel]:
        """
        Retrieve all documents for a specific session.

        Args:
            session: Async database session
            session_id: Parent session UUID
            limit: Maximum number of documents to return
            offset: Number of documents to skip

        Returns:
            Sequence of DocumentModels belonging to the session
        """
        stmt = (
            select(DocumentModel)
            .where(DocumentModel.session_id == session_id)
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_by_status(
        self,
        session: AsyncSession,
        status: DocumentStatus,
        limit: int | None = None,
    ) -> Sequence[DocumentModel]:
        """
        Retrieve documents by processing status.

        Args:
            session: Async database session
            status: Document processing status to filter by
            limit: Maximum number of documents to return

        Returns:
            Sequence of DocumentModels with matching status
        """
        stmt = select(DocumentModel).where(DocumentModel.status == status)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self,
        session: AsyncSession,
        id: UUID,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> DocumentModel | None:
        """
        Update document processing status.

        Args:
            session: Async database session
            id: Document UUID
            status: New processing status
            error_message: Error details if status is FAILED

        Returns:
            Updated DocumentModel if found, None otherwise
        """
        update_fields = {"status": status}
        if error_message is not None:
            update_fields["error_message"] = error_message
        return await self.update_by_id(session, id, **update_fields)

    async def mark_completed(
        self,
        session: AsyncSession,
        id: UUID,
    ) -> DocumentModel | None:
        """
        Mark document as successfully processed.

        Args:
            session: Async database session
            id: Document UUID

        Returns:
            Updated DocumentModel if found, None otherwise
        """
        return await self.update_status(session, id, DocumentStatus.COMPLETED)

    async def mark_failed(
        self,
        session: AsyncSession,
        id: UUID,
        error_message: str,
    ) -> DocumentModel | None:
        """
        Mark document as failed with error details.

        Args:
            session: Async database session
            id: Document UUID
            error_message: Human-readable error description

        Returns:
            Updated DocumentModel if found, None otherwise
        """
        return await self.update_status(
            session, id, DocumentStatus.FAILED, error_message
        )


document_crud = DocumentCRUD()
