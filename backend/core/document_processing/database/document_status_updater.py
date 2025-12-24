"""
Document status updater for RDS.

Updates document processing status in PostgreSQL:
PENDING → PROCESSING → COMPLETED (or FAILED with error message)

Self-contained database operations for Lambda deployment.
Uses DATABASE_URL environment variable for connection.

Dependencies: sqlalchemy, asyncpg
System role: Database persistence layer for Lambda
"""

import logging
import os
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)


class DocumentStatus(str, Enum):
    """Document processing lifecycle states (mirrors RDS schema)."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


def get_async_engine():
    """
    Create async engine from DATABASE_URL environment variable.

    Returns:
        AsyncEngine: SQLAlchemy async engine

    Raises:
        ValueError: DATABASE_URL not set
    """
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    # Convert postgres:// to postgresql+asyncpg://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return create_async_engine(
        database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        connect_args={"ssl": "require"},
    )


def get_async_session_factory() -> async_sessionmaker:
    """
    Create async session factory for Lambda use.

    Returns:
        async_sessionmaker: Session factory
    """
    engine = get_async_engine()
    return async_sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


class DocumentStatusUpdater:
    """Update document status in RDS during processing."""

    def __init__(self, db_session: AsyncSession) -> None:
        """
        Initialize with database session.

        Args:
            db_session: AsyncSession for RDS
        """
        self.db = db_session

    async def create_document(
        self,
        document_id: str,
        session_id: str,
        name: str,
        s3_key: str,
    ) -> None:
        """
        Create a new document record in RDS.
        
        Args:
            document_id: Document UUID
            session_id: Session UUID
            name: Filename
            s3_key: S3 object key (stored in upload_url)
        """
        try:
            from sqlalchemy import text
            
            stmt = text("""
                INSERT INTO documents (
                    id, session_id, name, status, upload_url, created_at, updated_at
                ) VALUES (
                    :id, :session_id, :name, :status, :upload_url, NOW(), NOW()
                )
            """)
            
            await self.db.execute(
                stmt,
                {
                    "id": document_id,
                    "session_id": session_id,
                    "name": name,
                    "status": DocumentStatus.PROCESSING.value,
                    "upload_url": s3_key,
                },
            )
            await self.db.commit()
            
            logger.info(
                f"{__name__}:create_document - Document created",
                extra={"document_id": document_id, "session_id": session_id},
            )

        except Exception as e:
            logger.error(f"{__name__}:create_document - {type(e).__name__}: {e}")
            await self.db.rollback()
            raise


    async def mark_processing(self, document_id: str) -> None:
        """
        Mark document as PROCESSING.

        Args:
            document_id: Document UUID

        Raises:
            ValueError: Document not found
        """
        try:
            from sqlalchemy import text

            # Use raw SQL update for simplicity (avoids needing ORM model import)
            stmt = text("""
                UPDATE documents
                SET status = :status, updated_at = NOW()
                WHERE id = :doc_id
                RETURNING id
            """)
            result = await self.db.execute(
                stmt,
                {"status": DocumentStatus.PROCESSING.value, "doc_id": document_id},
            )
            row = result.fetchone()

            if not row:
                raise ValueError(f"Document {document_id} not found")

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

        Args:
            document_id: Document UUID

        Raises:
            ValueError: Document not found
        """
        try:
            from sqlalchemy import text

            stmt = text("""
                UPDATE documents
                SET status = :status, error_message = NULL, updated_at = NOW()
                WHERE id = :doc_id
                RETURNING id
            """)
            result = await self.db.execute(
                stmt,
                {"status": DocumentStatus.COMPLETED.value, "doc_id": document_id},
            )
            row = result.fetchone()

            if not row:
                raise ValueError(f"Document {document_id} not found")

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

        Args:
            document_id: Document UUID
            error_message: Human-readable error description

        Raises:
            ValueError: Document not found
        """
        try:
            from sqlalchemy import text

            # Truncate error message to fit column (2048 chars)
            truncated_error = error_message[:2000] if len(error_message) > 2000 else error_message

            stmt = text("""
                UPDATE documents
                SET status = :status, error_message = :error_msg, updated_at = NOW()
                WHERE id = :doc_id
                RETURNING id
            """)
            result = await self.db.execute(
                stmt,
                {
                    "status": DocumentStatus.FAILED.value,
                    "error_msg": truncated_error,
                    "doc_id": document_id,
                },
            )
            row = result.fetchone()

            if not row:
                raise ValueError(f"Document {document_id} not found")

            await self.db.commit()

            logger.info(
                f"{__name__}:mark_failed - Document marked as FAILED",
                extra={"document_id": document_id, "error_message": truncated_error},
            )

        except Exception as e:
            logger.error(f"{__name__}:mark_failed - {type(e).__name__}: {e}")
            await self.db.rollback()
            raise
