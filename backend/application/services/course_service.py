"""
Course service orchestrator.

Coordinates course lifecycle operations.

Dependencies: backend.boundary.db.CRUD, backend.boundary.db.models
System role: Course use case orchestration
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.CRUD.course_crud import course_crud
from backend.boundary.db.CRUD.session_crud import session_crud

logger = logging.getLogger(__name__)


class CourseService:
    """Course service orchestrator."""

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialize course service with async database session.

        Args:
            db: Async SQLAlchemy session
        """
        self.db = db

    async def create_course(
        self,
        name: str,
        description: str | None = None,
        metadata: dict | None = None
    ) -> UUID:
        """
        Create new course with optional metadata.

        Args:
            name: Course name
            description: Course description (optional)
            metadata: Course metadata dict (optional)

        Returns:
            UUID: Created course ID

        Raises:
            Exception: If database operation fails
        """
        try:
            course = await course_crud.create(
                self.db,
                name=name,
                description=description,
                course_metadata=metadata or {}
            )
            logger.info(
                "Course created",
                extra={"course_id": str(course.id), "course_name": name}
            )
            return course.id
        except Exception as e:
            logger.error(
                "Failed to create course",
                extra={"error": str(e), "course_name": name}
            )
            raise

    async def get_course(self, course_id: UUID) -> dict:
        """
        Get course by ID.

        Args:
            course_id: Course UUID

        Returns:
            dict: Course data with id, name, description, metadata, timestamps

        Raises:
            ValueError: If course not found
        """
        try:
            course = await course_crud.get_by_id(self.db, course_id)

            if not course:
                raise ValueError(f"Course {course_id} does not exist")

            return {
                "id": course.id,
                "name": course.name,
                "description": course.description,
                "metadata": course.course_metadata,
                "created_at": course.created_at,
                "updated_at": course.updated_at,
            }
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get course",
                extra={"error": str(e), "course_id": str(course_id)}
            )
            raise

    async def get_all_courses(
        self,
        limit: int | None = None,
        offset: int = 0
    ) -> list[dict]:
        """
        Get all courses with pagination.

        Args:
            limit: Maximum number of courses to return
            offset: Number of courses to skip

        Returns:
            list[dict]: List of course dicts
        """
        try:
            courses = await course_crud.get_all(
                self.db,
                limit=limit,
                offset=offset
            )

            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "metadata": c.course_metadata,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
                for c in courses
            ]
        except Exception as e:
            logger.error("Failed to get all courses", extra={"error": str(e)})
            raise

    async def get_course_sessions(
        self,
        course_id: UUID,
        limit: int | None = None,
        offset: int = 0
    ) -> list[dict]:
        """
        Get sessions within a course.

        Args:
            course_id: Course UUID
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            list[dict]: List of session dicts for the course

        Raises:
            ValueError: If course not found
        """
        try:
            # Validate course exists
            course = await course_crud.get_by_id(self.db, course_id)
            if not course:
                raise ValueError(f"Course {course_id} does not exist")

            sessions = await course_crud.get_by_course_id(
                self.db,
                course_id,
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
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "Failed to get course sessions",
                extra={"error": str(e), "course_id": str(course_id)}
            )
            raise

    async def update_course(
        self,
        course_id: UUID,
        name: str | None = None,
        description: str | None = None
    ) -> dict:
        """
        Update course metadata.

        Args:
            course_id: Course UUID
            name: New course name (optional)
            description: New course description (optional)

        Returns:
            dict: Updated course data

        Raises:
            ValueError: If course not found
        """
        try:
            # Validate course exists
            course = await course_crud.get_by_id(self.db, course_id)
            if not course:
                raise ValueError(f"Course {course_id} does not exist")

            updates = {}
            if name is not None:
                updates["name"] = name
            if description is not None:
                updates["description"] = description

            if not updates:
                return {
                    "id": course.id,
                    "name": course.name,
                    "description": course.description,
                    "metadata": course.course_metadata,
                    "created_at": course.created_at,
                    "updated_at": course.updated_at,
                }

            updated = await course_crud.update_by_id(self.db, course_id, **updates)

            if not updated:
                raise ValueError(f"Course {course_id} does not exist")

            logger.info(
                "Course updated",
                extra={"course_id": str(course_id), "updates": list(updates.keys())}
            )

            return {
                "id": updated.id,
                "name": updated.name,
                "description": updated.description,
                "metadata": updated.course_metadata,
                "created_at": updated.created_at,
                "updated_at": updated.updated_at,
            }
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "Failed to update course",
                extra={"error": str(e), "course_id": str(course_id)}
            )
            raise

    async def delete_course(self, course_id: UUID) -> bool:
        """
        Delete course (sessions.course_id → NULL).

        Args:
            course_id: Course UUID

        Returns:
            bool: True if deleted

        Raises:
            ValueError: If course not found
        """
        try:
            deleted = await course_crud.delete_by_id(self.db, course_id)

            if not deleted:
                raise ValueError(f"Course {course_id} does not exist")

            logger.info("Course deleted", extra={"course_id": str(course_id)})
            return True
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                "Failed to delete course",
                extra={"error": str(e), "course_id": str(course_id)}
            )
            raise
