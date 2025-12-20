"""
Image CRUD operations for visual knowledge diagrams.

Provides Create, Read, Update, Delete operations for ImageModel
with image-specific query methods for session filtering and ordering.

Dependencies: sqlalchemy, uuid, backend.boundary.db.models
System role: Image metadata persistence for visual diagrams
"""

from typing import Sequence
from uuid import UUID

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.models.image_model import ImageModel
from backend.boundary.db.CRUD.base_crud import BaseCRUD


class ImageCRUD(BaseCRUD[ImageModel]):
    """
    CRUD operations for ImageModel.

    Extends BaseCRUD with image-specific queries for filtering
    by session, ordering by creation time, and retrieving by message index.
    """

    def __init__(self) -> None:
        """Initialize ImageCRUD with ImageModel."""
        super().__init__(ImageModel)

    async def get_by_session_id(
        self,
        session: AsyncSession,
        session_id: UUID,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[ImageModel]:
        """
        Retrieve all images for a specific session, ordered by creation (newest first).

        Args:
            session: Async database session
            session_id: Parent session UUID
            limit: Maximum number of images to return
            offset: Number of images to skip

        Returns:
            Sequence of ImageModels belonging to the session, newest first
        """
        stmt = (
            select(ImageModel)
            .where(ImageModel.session_id == session_id)
            .order_by(desc(ImageModel.created_at))
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_by_message_index(
        self,
        session: AsyncSession,
        session_id: UUID,
        message_index: int,
    ) -> ImageModel | None:
        """
        Retrieve image linked to specific chat message position.

        Args:
            session: Async database session
            session_id: Parent session UUID
            message_index: Position in chat history (0-indexed)

        Returns:
            ImageModel if found, None otherwise
        """
        stmt = (
            select(ImageModel)
            .where(
                (ImageModel.session_id == session_id)
                & (ImageModel.message_index == message_index)
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_session(
        self,
        session: AsyncSession,
        session_id: UUID,
    ) -> ImageModel | None:
        """
        Retrieve most recently created image for a session.

        Args:
            session: Async database session
            session_id: Parent session UUID

        Returns:
            Most recent ImageModel if any exist, None otherwise
        """
        stmt = (
            select(ImageModel)
            .where(ImageModel.session_id == session_id)
            .order_by(desc(ImageModel.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_from_generation(
        self,
        session: AsyncSession,
        session_id: UUID,
        s3_key: str,
        mime_type: str,
        main_concepts: list[str],
        branches: list[dict],
        image_generation_prompt: str,
        message_index: int | None = None,
    ) -> ImageModel:
        """
        Create image record from generation output.

        Args:
            session: Async database session
            session_id: Parent session UUID
            s3_key: S3 object key for image
            mime_type: Image MIME type (e.g., image/png)
            main_concepts: List of main concept strings
            branches: List of branch dictionaries with id, label, description
            image_generation_prompt: Full prompt sent to Gemini
            message_index: Optional chat message position

        Returns:
            Created ImageModel instance with all metadata
        """
        return await self.create(
            session,
            session_id=session_id,
            s3_key=s3_key,
            mime_type=mime_type,
            message_index=message_index,
            main_concepts=main_concepts,
            branches=branches,
            image_generation_prompt=image_generation_prompt,
        )


image_crud = ImageCRUD()
