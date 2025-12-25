"""
Course API endpoints.

Routes:
- POST /courses - Create new course
- GET /courses - List all courses
- GET /courses/{id} - Get single course
- PUT /courses/{id} - Update course
- DELETE /courses/{id} - Delete course
- GET /courses/{id}/sessions - List sessions in course
- POST /courses/{id}/sessions - Create session in course

Dependencies: backend.application.services, backend.models
System role: Course management HTTP API
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends

from backend.application.services.course_service import CourseService
from backend.application.services.session_service import SessionService
from backend.api.deps.dependencies import (
    get_course_service,
    get_session_service,
)
from backend.models.course import (
    CreateCourseRequest,
    UpdateCourseRequest,
    CourseResponse,
)
from backend.models.session import CreateSessionRequest, SessionResponse

from .course_error_handling import handle_course_errors
from .course_validators import (
    validate_course_creation,
    validate_course_update,
)
from .course_responses import (
    map_course_to_response,
    map_courses_to_response,
    map_session_to_response,
    map_sessions_to_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("", response_model=CourseResponse, status_code=201)
@handle_course_errors
async def create_course(
    request: CreateCourseRequest,
    course_service: CourseService = Depends(get_course_service),
) -> CourseResponse:
    """
    Create new course with optional metadata.

    Args:
        request: CreateCourseRequest with name, description, metadata
        course_service: Injected CourseService

    Returns:
        CourseResponse: Created course

    Raises:
        HTTPException(400): Invalid request
        HTTPException(500): Creation failed
    """
    # Business validation
    validate_course_creation(request)

    logger.info(
        "Creating new course",
        extra={"course_name": request.name, "has_description": bool(request.description)}
    )

    course_id = await course_service.create_course(
        name=request.name,
        description=request.description,
        metadata=request.metadata or {}
    )
    course_data = await course_service.get_course(course_id)

    logger.info(
        "Course created successfully",
        extra={"course_id": str(course_id), "course_name": request.name}
    )

    return map_course_to_response(course_data)


@router.get("", response_model=list[CourseResponse])
@handle_course_errors
async def list_courses(
    limit: int = 100,
    offset: int = 0,
    course_service: CourseService = Depends(get_course_service),
) -> list[CourseResponse]:
    """
    List all courses with pagination.

    Args:
        limit: Maximum number of courses (default 100)
        offset: Number to skip (default 0)
        course_service: Injected CourseService

    Returns:
        list[CourseResponse]: List of courses

    Raises:
        HTTPException(500): Retrieval failed
    """
    logger.info(
        "Listing courses",
        extra={"limit": limit, "offset": offset}
    )

    courses = await course_service.get_all_courses(limit=limit, offset=offset)

    logger.info(
        "Courses retrieved successfully",
        extra={"count": len(courses), "limit": limit, "offset": offset}
    )

    return map_courses_to_response(courses)


@router.get("/{course_id}", response_model=CourseResponse)
@handle_course_errors
async def get_course(
    course_id: UUID,
    course_service: CourseService = Depends(get_course_service),
) -> CourseResponse:
    """
    Get single course by ID.

    Args:
        course_id: Course UUID
        course_service: Injected CourseService

    Returns:
        CourseResponse: Course data

    Raises:
        HTTPException(404): Course not found
        HTTPException(500): Retrieval failed
    """
    logger.info(
        "Fetching course",
        extra={"course_id": str(course_id)}
    )

    course_data = await course_service.get_course(course_id)

    logger.info(
        "Course retrieved successfully",
        extra={"course_id": str(course_id), "course_name": course_data.get("name")}
    )

    return map_course_to_response(course_data)


@router.put("/{course_id}", response_model=CourseResponse)
@handle_course_errors
async def update_course(
    course_id: UUID,
    request: UpdateCourseRequest,
    course_service: CourseService = Depends(get_course_service),
) -> CourseResponse:
    """
    Update course by ID.

    Args:
        course_id: Course UUID
        request: UpdateCourseRequest with optional name, description
        course_service: Injected CourseService

    Returns:
        CourseResponse: Updated course

    Raises:
        HTTPException(404): Course not found
        HTTPException(400): Invalid request
        HTTPException(500): Update failed
    """
    # Business validation
    validate_course_update(request)

    logger.info(
        "Updating course",
        extra={
            "course_id": str(course_id),
            "updating_name": request.name is not None,
            "updating_description": request.description is not None
        }
    )

    course_data = await course_service.update_course(
        course_id=course_id,
        name=request.name,
        description=request.description
    )

    logger.info(
        "Course updated successfully",
        extra={"course_id": str(course_id), "course_name": course_data.get("name")}
    )

    return map_course_to_response(course_data)


@router.delete("/{course_id}", status_code=204)
@handle_course_errors
async def delete_course(
    course_id: UUID,
    course_service: CourseService = Depends(get_course_service),
) -> None:
    """
    Delete course by ID (sessions preserved with course_id = NULL).

    Args:
        course_id: Course UUID
        course_service: Injected CourseService

    Returns:
        204 No Content on success

    Raises:
        HTTPException(404): Course not found
        HTTPException(500): Deletion failed
    """
    logger.info(
        "Deleting course",
        extra={"course_id": str(course_id)}
    )

    await course_service.delete_course(course_id)

    logger.info(
        "Course deleted successfully",
        extra={"course_id": str(course_id)}
    )


@router.get("/{course_id}/sessions", response_model=list[SessionResponse])
@handle_course_errors
async def get_course_sessions(
    course_id: UUID,
    limit: int = 100,
    offset: int = 0,
    course_service: CourseService = Depends(get_course_service),
) -> list[SessionResponse]:
    """
    List all sessions in a course.

    Args:
        course_id: Course UUID
        limit: Maximum number of sessions (default 100)
        offset: Number to skip (default 0)
        course_service: Injected CourseService

    Returns:
        list[SessionResponse]: List of sessions in course

    Raises:
        HTTPException(404): Course not found
        HTTPException(500): Retrieval failed
    """
    logger.info(
        "Fetching course sessions",
        extra={"course_id": str(course_id), "limit": limit, "offset": offset}
    )

    sessions = await course_service.get_course_sessions(
        course_id=course_id,
        limit=limit,
        offset=offset
    )

    logger.info(
        "Course sessions retrieved successfully",
        extra={"course_id": str(course_id), "session_count": len(sessions), "limit": limit, "offset": offset}
    )

    return map_sessions_to_response(sessions)


@router.post("/{course_id}/sessions", response_model=SessionResponse, status_code=201)
@handle_course_errors
async def create_course_session(
    course_id: UUID,
    request: CreateSessionRequest,
    session_service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    """
    Create new session within a course.

    Args:
        course_id: Course UUID
        request: CreateSessionRequest with optional metadata
        session_service: Injected SessionService

    Returns:
        SessionResponse: Created session with course_id

    Raises:
        HTTPException(404): Course not found
        HTTPException(400): Invalid request
        HTTPException(500): Creation failed
    """
    logger.info(
        "Creating session in course",
        extra={"course_id": str(course_id), "has_metadata": bool(request.metadata)}
    )

    metadata = request.metadata or {}
    session_id = await session_service.create_session(
        metadata=metadata,
        course_id=course_id
    )
    session_data = await session_service.get_session(session_id)

    logger.info(
        "Session created in course successfully",
        extra={"course_id": str(course_id), "session_id": str(session_id)}
    )

    return map_session_to_response(session_data)
