"""
Presigned URL utilities.

Validation and S3 key generation helpers for document uploads.

Dependencies: None
System role: Presigned URL request validation
"""

import uuid


# Allowed file extensions for document upload
ALLOWED_EXTENSIONS = {"pdf"}


class FilenameValidationError(ValueError):
    """Raised when filename validation fails."""

    pass


def validate_filename(filename: str) -> None:
    """
    Validate filename for security and allowed extensions.

    Args:
        filename: Original filename from user

    Raises:
        FilenameValidationError: If filename is invalid or not allowed
    """
    if not filename or len(filename) > 255:
        raise FilenameValidationError("Invalid filename length")

    # Block path traversal attacks
    if ".." in filename or "/" in filename or "\\" in filename:
        raise FilenameValidationError("Invalid filename: path traversal detected")

    # Check file extension is present
    if "." not in filename:
        raise FilenameValidationError("File must have an extension")

    # Check file extension is allowed
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FilenameValidationError(
            f"File type '.{ext}' not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )


def generate_safe_s3_key(session_id: str, filename: str) -> str:
    """
    Generate unique S3 key to prevent collisions and security issues.

    Format: sessions/{session_id}/documents/{unique_id}-{sanitized_name}.{ext}

    Args:
        session_id: Session UUID as string
        filename: Original filename from user

    Returns:
        str: Safe S3 key path
    """
    # Extract file extension
    file_ext = ""
    if "." in filename:
        file_ext = "." + filename.rsplit(".", 1)[-1].lower()

    # Sanitize filename (only alphanumeric, dots, hyphens, underscores)
    base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
    safe_name = "".join(c for c in base_name if c.isalnum() or c in "-_")
    if not safe_name:
        safe_name = "document"

    # Add unique prefix to prevent collisions
    unique_id = str(uuid.uuid4())[:8]

    return f"sessions/{session_id}/documents/{unique_id}-{safe_name}{file_ext}"
