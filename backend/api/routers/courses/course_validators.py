"""
Course validation utilities.

Business logic validation not covered by Pydantic models.
These validators check domain-specific rules.

Dependencies: backend.models.course
System role: Course business logic validation
"""

from backend.models.course import CreateCourseRequest, UpdateCourseRequest


class CourseValidationError(ValueError):
    """Raised when course validation fails."""


def validate_course_creation(request: CreateCourseRequest) -> None:
    """
    Validate course creation request with business rules.

    Args:
        request: CreateCourseRequest with name, description, metadata

    Raises:
        CourseValidationError: If business validation fails
    """
    # Name validation
    if not request.name or not request.name.strip():
        raise CourseValidationError("Course name cannot be empty or whitespace-only")

    if len(request.name.strip()) < 2:
        raise CourseValidationError("Course name must be at least 2 characters")

    if len(request.name) > 255:
        raise CourseValidationError("Course name cannot exceed 255 characters")

    # Description validation (optional but if present, must be reasonable)
    if request.description and len(request.description) > 5000:
        raise CourseValidationError("Course description cannot exceed 5000 characters")

    # Metadata validation (optional)
    if request.metadata:
        if not isinstance(request.metadata, dict):
            raise CourseValidationError("Metadata must be a dictionary")
        # Limit metadata size to prevent abuse
        if len(str(request.metadata)) > 10000:
            raise CourseValidationError("Metadata payload too large")


def validate_course_update(request: UpdateCourseRequest) -> None:
    """
    Validate course update request with business rules.

    Args:
        request: UpdateCourseRequest with optional name, description

    Raises:
        CourseValidationError: If business validation fails
    """
    # At least one field should be provided for update
    if request.name is None and request.description is None:
        raise CourseValidationError("At least one field must be provided for update")

    # Name validation (if provided)
    if request.name is not None:
        if not request.name.strip():
            raise CourseValidationError("Course name cannot be empty or whitespace-only")

        if len(request.name.strip()) < 2:
            raise CourseValidationError("Course name must be at least 2 characters")

        if len(request.name) > 255:
            raise CourseValidationError("Course name cannot exceed 255 characters")

    # Description validation (if provided)
    if request.description is not None and len(request.description) > 5000:
        raise CourseValidationError("Course description cannot exceed 5000 characters")
