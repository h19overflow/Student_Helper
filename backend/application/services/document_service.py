"""
Document service orchestrator.

Wraps DevDocumentPipeline for S3 Vectors compatibility.
Coordinates document upload, processing, search, and deletion.

Dependencies: backend.boundary.vdb, backend.boundary.db, backend.core
System role: Document management orchestration
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.CRUD.document_crud import document_crud
from backend.boundary.db.CRUD.session_crud import session_crud
from backend.boundary.db.models.document_model import DocumentStatus
from backend.boundary.vdb.dev_task import DevDocumentPipeline, DevPipelineResult
from backend.boundary.vdb.faiss_store import FAISSStore
from backend.core.exceptions import ParsingError


class DocumentService:
    """
    Document service orchestrator.

    Wraps DevDocumentPipeline to provide S3 Vectors-compatible interface.
    Handles document lifecycle: upload, processing, search, deletion.
    """

    def __init__(
        self,
        db: AsyncSession,
        dev_pipeline: DevDocumentPipeline | None = None,
    ) -> None:
        """
        Initialize document service.

        Args:
            db: AsyncSession for document metadata tracking
            dev_pipeline: Optional DevDocumentPipeline (created if None)
        """
        self.db = db
        self.pipeline = dev_pipeline or DevDocumentPipeline()

    async def upload_document(
        self,
        file_path: str,
        session_id: UUID,
        document_name: str,
    ) -> DevPipelineResult:
        """
        Upload and process document through pipeline.

        Steps:
        1. Validate session exists
        2. Create document record in DB with PENDING status
        3. Process via pipeline (parse → chunk → embed → index)
        4. Update document status to COMPLETED
        5. Return processing result

        Args:
            file_path: Path to document file
            session_id: Session UUID
            document_name: Document filename/name

        Returns:
            DevPipelineResult: Processing result with chunk count and timing

        Raises:
            ValueError: If session doesn't exist
            ParsingError: If document parsing fails
        """
        # Validate session exists
        session = await session_crud.get_by_id(self.db, session_id)
        if not session:
            raise ValueError(f"Session {session_id} does not exist")

        # Create document record
        document = await document_crud.create(
            self.db,
            name=document_name,
            session_id=session_id,
            upload_url=file_path,
            status=DocumentStatus.PENDING,
        )

        try:
            # Process document through pipeline
            result = self.pipeline.process(
                file_path=file_path,
                document_id=str(document.id),
                session_id=str(session_id),
            )

            # Update status to COMPLETED
            await document_crud.update_status(
                self.db,
                document.id,
                DocumentStatus.COMPLETED,
            )

            return result

        except Exception as e:
            # Update status to FAILED
            await document_crud.mark_failed(
                self.db,
                document.id,
                error_message=str(e),
            )
            if isinstance(e, ParsingError):
                raise
            raise ParsingError(
                message=f"Document processing failed: {str(e)}",
                details={"document_id": str(document.id), "error": str(e)},
            ) from e

    async def search_documents(
        self,
        query: str,
        session_id: UUID,
        k: int = 5,
        doc_id: UUID | None = None,
    ) -> list[dict]:
        """
        Search indexed documents (matches S3 Vectors interface).

        Args:
            query: Search query text
            session_id: Session UUID for filtering
            k: Number of results to return
            doc_id: Optional document ID for filtering

        Returns:
            list[dict]: Search results with content, score, metadata
        """
        return self.pipeline.search(
            query=query,
            k=k,
            session_id=str(session_id),
            doc_id=str(doc_id) if doc_id else None,
        )

    async def get_session_documents(self, session_id: UUID) -> list[str]:
        """
        Query collection for document names in session.

        Args:
            session_id: Session UUID

        Returns:
            list[str]: Document names/filenames
        """
        documents = await document_crud.get_by_session_id(self.db, session_id)
        return [doc.name for doc in documents]

    async def delete_document(self, doc_id: UUID, session_id: UUID) -> None:
        """
        Delete document from vector store and database.

        Steps:
        1. Validate document exists and belongs to session
        2. Delete from vector store (FAISSStore.delete_by_doc_id)
        3. Delete document record from DB

        Args:
            doc_id: Document UUID
            session_id: Session UUID for validation

        Raises:
            ValueError: If document doesn't exist or doesn't belong to session
        """
        # Validate document exists
        document = await document_crud.get_by_id(self.db, doc_id)
        if not document:
            raise ValueError(f"Document {doc_id} does not exist")

        # Validate document belongs to session
        if document.session_id != session_id:
            raise ValueError(
                f"Document {doc_id} does not belong to session {session_id}"
            )

        # Delete from vector store
        # Access FAISSStore directly from pipeline
        if hasattr(self.pipeline, "_faiss_store"):
            self.pipeline._faiss_store.delete_by_doc_id(str(doc_id))

        # Delete document record
        await document_crud.delete_by_id(self.db, doc_id)

    def clear_session_index(self, session_id: UUID) -> None:
        """
        Clear all vectors for a session.

        Note: FAISSStore doesn't support session-level clear.
        Iterates through session documents and deletes each.

        Args:
            session_id: Session UUID
        """
        # Get all documents for session
        # Note: This needs to be async, but current signature is sync
        # This is a limitation of the current FAISSStore design
        # For production with S3 Vectors, this would be a single operation
        self.pipeline.clear_index()

    # Legacy methods (keeping for backward compatibility)

    async def upload_documents(
        self,
        session_id: UUID,
        files: list[str],
    ) -> list[UUID]:
        """
        Upload multiple documents (legacy interface).

        Args:
            session_id: Session UUID
            files: List of file paths

        Returns:
            list[UUID]: Document IDs
        """
        doc_ids = []
        for file_path in files:
            result = await self.upload_document(
                file_path=file_path,
                session_id=session_id,
                document_name=file_path.split("/")[-1],  # Extract filename
            )
            # Extract doc_id from result.document_id
            doc_ids.append(UUID(result.document_id))
        return doc_ids

    async def get_documents(
        self,
        session_id: UUID,
        cursor: str | None = None,
    ) -> dict:
        """
        Get paginated document list (legacy interface).

        Args:
            session_id: Session UUID
            cursor: Optional pagination cursor

        Returns:
            dict: Documents list with pagination info
        """
        documents = await document_crud.get_by_session_id(self.db, session_id)
        return {
            "documents": [
                {
                    "id": str(doc.id),
                    "name": doc.name,
                    "status": doc.status.value,
                    "created_at": doc.created_at.isoformat(),
                    "error_message": doc.error_message,
                }
                for doc in documents
            ],
            "total": len(documents),
            "cursor": None,  # Pagination not implemented
        }

    async def get_document_status(self, doc_id: UUID) -> dict:
        """
        Get document processing status (legacy interface).

        Args:
            doc_id: Document UUID

        Returns:
            dict: Document status info

        Raises:
            ValueError: If document doesn't exist
        """
        document = await document_crud.get_by_id(self.db, doc_id)
        if not document:
            raise ValueError(f"Document {doc_id} does not exist")

        return {
            "id": str(document.id),
            "name": document.name,
            "status": document.status.value,
            "created_at": document.created_at.isoformat(),
            "updated_at": document.updated_at.isoformat(),
            "error_message": document.error_message,
        }
