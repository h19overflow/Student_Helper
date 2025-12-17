"""
Document service orchestrator.

Coordinates document upload, processing, search, and deletion.
Uses DocumentPipeline for S3 Vectors integration.

Dependencies: backend.boundary.vdb, backend.boundary.db, backend.core
System role: Document management orchestration
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.CRUD.document_crud import document_crud
from backend.boundary.db.CRUD.session_crud import session_crud
from backend.boundary.db.models.document_model import DocumentStatus
from backend.boundary.vdb.s3_vectors_store import S3VectorsStore
from backend.core.document_processing.entrypoint import DocumentPipeline
from backend.core.document_processing.models import PipelineResult
from backend.core.exceptions import ParsingError


class DocumentService:
    """
    Document service orchestrator.

    Uses DocumentPipeline for S3 Vectors upload and S3VectorsStore for retrieval.
    Handles document lifecycle: upload, processing, search, deletion.
    """

    def __init__(
        self,
        db: AsyncSession,
        pipeline: DocumentPipeline | None = None,
        vector_store: S3VectorsStore | None = None,
    ) -> None:
        """
        Initialize document service.

        Args:
            db: AsyncSession for document metadata tracking
            pipeline: Optional DocumentPipeline (created if None)
            vector_store: Optional S3VectorsStore for search (created if None)
        """
        self.db = db
        self._pipeline = pipeline
        self._vector_store = vector_store

    @property
    def pipeline(self) -> DocumentPipeline:
        """Lazy-load pipeline to avoid initialization cost."""
        if self._pipeline is None:
            self._pipeline = DocumentPipeline()
        return self._pipeline

    @property
    def vector_store(self) -> S3VectorsStore:
        """Lazy-load vector store to avoid initialization cost."""
        if self._vector_store is None:
            self._vector_store = S3VectorsStore()
        return self._vector_store

    async def upload_document(
        self,
        session_id: UUID,
        document_name: str,
        file_path: str | None = None,
        s3_key: str | None = None,
    ) -> PipelineResult:
        """
        Upload and process document through pipeline.

        Accepts either a local file_path OR an s3_key. If s3_key is provided,
        the pipeline downloads from S3 first, then processes.

        Steps:
        1. Validate session exists
        2. Create document record in DB with PENDING status
        3. Process via pipeline (S3 download → parse → chunk → embed+upload to S3 Vectors)
        4. Update document status to COMPLETED
        5. Return processing result

        Args:
            session_id: Session UUID
            document_name: Document filename/name
            file_path: Path to local document file (mutually exclusive with s3_key)
            s3_key: S3 object key (mutually exclusive with file_path)

        Returns:
            PipelineResult: Processing result with chunk count and timing

        Raises:
            ValueError: If session doesn't exist or neither file_path nor s3_key provided
            ParsingError: If document parsing fails
        """
        if not file_path and not s3_key:
            raise ValueError("Either file_path or s3_key must be provided")

        # Validate session exists
        session = await session_crud.get_by_id(self.db, session_id)
        if not session:
            raise ValueError(f"Session {session_id} does not exist")

        # Use s3_key as upload_url if provided, otherwise use file_path
        upload_url = s3_key if s3_key else file_path

        # Create document record
        document = await document_crud.create(
            self.db,
            name=document_name,
            session_id=session_id,
            upload_url=upload_url,
            status=DocumentStatus.PENDING,
        )

        try:
            # Process document through pipeline
            result = self.pipeline.process(
                file_path=file_path,
                s3_key=s3_key,
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
        Search indexed documents via S3 Vectors.

        Args:
            query: Search query text
            session_id: Session UUID for filtering
            k: Number of results to return
            doc_id: Optional document ID for filtering

        Returns:
            list[dict]: Search results with content, score, metadata
        """
        results = self.vector_store.similarity_search(
            query=query,
            k=k,
            session_id=str(session_id),
            doc_id=str(doc_id) if doc_id else None,
        )
        return [
            {
                "content": r.content,
                "score": r.similarity_score,
                "metadata": r.metadata.model_dump(),
            }
            for r in results
        ]

    async def get_session_documents(self, session_id: UUID):
        """
        Query collection for documents in session.

        Args:
            session_id: Session UUID

        Returns:
            Sequence[DocumentModel]: Document records from database
        """
        documents = await document_crud.get_by_session_id(self.db, session_id)
        return documents

    async def delete_document(self, doc_id: UUID, session_id: UUID) -> None:
        """
        Delete document from vector store and database.

        Steps:
        1. Validate document exists and belongs to session
        2. Delete from S3 Vectors
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

        # Query S3 Vectors for all chunks belonging to this document
        # Use a dummy query since we're filtering by doc_id metadata
        search_results = self.vector_store.similarity_search(
            query="",
            k=1000,  # Get all chunks for this document
            doc_id=str(doc_id),
        )

        # Extract chunk IDs from search results
        chunk_ids = [result.chunk_id for result in search_results]

        # Delete chunks from S3 Vectors if any exist
        if chunk_ids:
            self.vector_store.delete_by_doc_id(str(doc_id), chunk_ids)

        # Delete document record from database
        await document_crud.delete_by_id(self.db, doc_id)



