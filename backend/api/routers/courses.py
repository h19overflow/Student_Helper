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

from fastapi import APIRouter, Depends, HTTPException

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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/courses", tags=["courses"])


@router.post("", response_model=CourseResponse, status_code=201)
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
    try:
        course_id = await course_service.create_course(
            name=request.name,
            description=request.description,
            metadata=request.metadata or {}
        )
        course_data = await course_service.get_course(course_id)
        return CourseResponse(**course_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Course creation failed: {str(e)}"
        )


@router.get("", response_model=list[CourseResponse])
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
    try:
        courses = await course_service.get_all_courses(limit=limit, offset=offset)
        return [CourseResponse(**course) for course in courses]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve courses: {str(e)}"
        )


@router.get("/{course_id}", response_model=CourseResponse)
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
    try:
        course_data = await course_service.get_course(course_id)
        return CourseResponse(**course_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Course retrieval failed: {str(e)}"
        )


@router.put("/{course_id}", response_model=CourseResponse)
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
    try:
        course_data = await course_service.update_course(
            course_id=course_id,
            name=request.name,
            description=request.description
        )
        return CourseResponse(**course_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Course update failed: {str(e)}"
        )


@router.delete("/{course_id}", status_code=204)
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
    try:
        await course_service.delete_course(course_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Course deletion failed: {str(e)}"
        )


@router.get("/{course_id}/sessions", response_model=list[SessionResponse])
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
    try:
        sessions = await course_service.get_course_sessions(
            course_id=course_id,
            limit=limit,
            offset=offset
        )
        return [SessionResponse(**session) for session in sessions]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve course sessions: {str(e)}"
        )


@router.post("/{course_id}/sessions", response_model=SessionResponse, status_code=201)
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
    try:
        metadata = request.metadata or {}
        session_id = await session_service.create_session(
            metadata=metadata,
            course_id=course_id
        )
        session_data = await session_service.get_session(session_id)
        return SessionResponse(**session_data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Session creation failed: {str(e)}"
        )
