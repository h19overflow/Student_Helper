"""
Course response mapping utilities.

Transforms DTOs, ORM models, and dictionaries into Pydantic response models.
Centralizes response construction logic.

Dependencies: backend.models.course, backend.models.session
System role: Course response transformation
"""

from typing import Any

from backend.models.course import CourseResponse
from backend.models.session import SessionResponse


def map_course_to_response(course_data: dict[str, Any]) -> CourseResponse:
    """
    Transform course data dictionary into CourseResponse.

    Args:
        course_data: Dictionary containing course fields
            Expected keys: id, name, description, metadata, created_at, updated_at

    Returns:
        CourseResponse: Pydantic model for API response
    """
    return CourseResponse(**course_data)


def map_courses_to_response(courses_data: list[dict[str, Any]]) -> list[CourseResponse]:
    """
    Transform list of course dictionaries into list of CourseResponse.

    Args:
        courses_data: List of course dictionaries

    Returns:
        list[CourseResponse]: List of Pydantic models for API response
    """
    return [map_course_to_response(course) for course in courses_data]


def map_session_to_response(session_data: dict[str, Any]) -> SessionResponse:
    """
    Transform session data dictionary into SessionResponse.

    Args:
        session_data: Dictionary containing session fields
            Expected keys: id, course_id, metadata, created_at

    Returns:
        SessionResponse: Pydantic model for API response
    """
    return SessionResponse(**session_data)


def map_sessions_to_response(sessions_data: list[dict[str, Any]]) -> list[SessionResponse]:
    """
    Transform list of session dictionaries into list of SessionResponse.

    Args:
        sessions_data: List of session dictionaries

    Returns:
        list[SessionResponse]: List of Pydantic models for API response
    """
    return [map_session_to_response(session) for session in sessions_data]
