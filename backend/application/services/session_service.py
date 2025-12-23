"""
Session service orchestrator.

Coordinates session lifecycle operations.

Dependencies: backend.boundary.db.CRUD, backend.boundary.db.models
System role: Session use case orchestration
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.CRUD.session_crud import session_crud
from backend.boundary.db.CRUD.course_crud import course_crud


class SessionService:
    """Session service orchestrator."""

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize session service with async database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db

    async def create_session(
        self,
        metadata: dict,
        course_id: UUID | None = None
    ) -> UUID:
        """
        Create new session with optional metadata and course context.

        Args:
            metadata: Session metadata dict
            course_id: Optional parent course ID

        Returns:
            UUID: Created session ID

        Raises:
            ValueError: If course_id provided but course not found
            Exception: If database operation fails
        """
        # Validate course exists if course_id provided
        if course_id is not None:
            course = await course_crud.get_by_id(self.db, course_id)
            if not course:
                raise ValueError(f"Course {course_id} does not exist")

        session = await session_crud.create(
            self.db,
            session_metadata=metadata,
            course_id=course_id
        )
        return session.id

    async def get_session(self, session_id: UUID) -> dict:
        """
        Get session by ID.

        Args:
            session_id: Session UUID

        Returns:
            dict: Session data with id, course_id, metadata, created_at, updated_at

        Raises:
            ValueError: If session not found
        """
        session = await session_crud.get_by_id(self.db, session_id)

        if not session:
            raise ValueError(f"Session {session_id} does not exist")

        return {
            "id": session.id,
            "course_id": session.course_id,
            "metadata": session.session_metadata,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }

    async def get_all_sessions(
        self,
        limit: int | None = None,
        offset: int = 0
    ) -> list[dict]:
        """
        Get all sessions with pagination.

        Args:
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            list[dict]: List of session dicts with course context
        """
        sessions = await session_crud.get_all(
            self.db,
            limit=limit,
            offset=offset
        )

        return [
            {
                "id": s.id,
                "course_id": s.course_id,
                "metadata": s.session_metadata,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in sessions
        ]

    async def delete_session(self, session_id: UUID) -> bool:
        """
        Delete session by ID.

        Args:
            session_id: Session UUID

        Returns:
            bool: True if deleted, False if not found

        Raises:
            ValueError: If session not found
        """
        deleted = await session_crud.delete_by_id(self.db, session_id)

        if not deleted:
            raise ValueError(f"Session {session_id} does not exist")

        return True

    async def add_chat_message(
        self,
        session_id: UUID,
        message: str,
        response: str
    ) -> None:
        """Add chat message to session history (placeholder for future)."""
        pass
