"""
Course error handling utilities.

Provides custom exceptions and a decorator for consistent error handling 
across course-related API endpoints.
"""

import functools
import logging
from typing import Any, Callable, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Type for the decorated function
F = TypeVar("F", bound=Callable[..., Any])

class CourseError(Exception):
    """Base class for course-related errors."""
    def __init__(self, message: str, course_id: UUID | None = None):
        self.message = message
        self.course_id = course_id
        super().__init__(self.message)

class CourseNotFoundError(CourseError):
    """Raised when a course is not found."""
    pass

class CourseAlreadyExistsError(CourseError):
    """Raised when a course with the same unique identifier already exists."""
    pass

class InvalidCourseDataError(CourseError):
    """Raised when course data is invalid."""
    pass

class CourseOperationError(CourseError):
    """Raised when a course operation fails at the service or boundary layer."""
    pass

def handle_course_errors(func: F) -> F:
    """
    Decorator to handle course-related errors and transform them into HTTPExceptions.
    
    This centralizes:
    - Logging of errors with context (course_id)
    - Mapping specific exceptions to HTTP status codes
    - Ensuring uniform error response formats
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        
        except CourseNotFoundError as e:
            logger.warning(
                "Course not found",
                extra={"course_id": str(e.course_id), "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
            
        except (CourseAlreadyExistsError, InvalidCourseDataError) as e:
            logger.warning(
                "Invalid course request",
                extra={"course_id": str(e.course_id) if e.course_id else None, "error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
            
        except ValueError as e:
            # Handle generic ValueErrors from service layer as 404/400 based on context
            msg = str(e).lower()
            if "not found" in msg or "does not exist" in msg:
                logger.warning("Resource not found (ValueError)", extra={"error": str(e)})
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
            else:
                logger.warning("Invalid request (ValueError)", extra={"error": str(e)})
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
                
        except ValidationError as e:
            logger.warning("Pydantic validation error", extra={"error": str(e)})
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=e.errors()
            )
            
        except Exception as e:
            logger.exception(
                "Unexpected failure in course operation",
                extra={"error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An internal error occurred during course operation: {str(e)}"
            )
            
    return wrapper # type: ignore
