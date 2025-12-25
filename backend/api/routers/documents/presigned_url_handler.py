"""
Presigned URL handler.

Encapsulates filename validation and S3 key generation for document uploads.

Dependencies: backend.api.routers.router_utils.presigned_url_utils, backend.boundary.aws.s3_client
System role: Presigned URL request handling
"""

import logging
from uuid import UUID

from backend.api.routers.router_utils.presigned_url_utils import (
    FilenameValidationError,
    generate_safe_s3_key,
    validate_filename,
)
from backend.boundary.aws.s3_client import S3DocumentClient
from backend.models.document import PresignedUrlRequest, PresignedUrlResponse

logger = logging.getLogger(__name__)


class PresignedUrlError(Exception):
    """Base exception for presigned URL handling errors."""


class FilenameError(PresignedUrlError):
    """Raised when filename validation fails."""

    def __init__(self, message: str, filename: str):
        self.filename = filename
        super().__init__(message)


class S3PresignError(PresignedUrlError):
    """Raised when S3 presigned URL generation fails."""


def handle_presigned_url_request(
    session_id: UUID,
    request: PresignedUrlRequest,
    s3_client: S3DocumentClient,
) -> PresignedUrlResponse:
    """
    Generate presigned URL for direct S3 upload.

    Validates the filename, generates a safe S3 key, and creates
    a presigned URL for the client to upload directly to S3.

    Args:
        session_id: Session UUID
        request: PresignedUrlRequest with filename and content_type
        s3_client: S3DocumentClient for URL generation

    Returns:
        PresignedUrlResponse: Presigned URL, s3_key, and expiry

    Raises:
        FilenameError: Invalid filename or extension
        S3PresignError: Failed to generate presigned URL
    """
    logger.info(
        "Processing presigned URL request",
        extra={"session_id": str(session_id), "file_name": request.filename},
    )

    try:
        # Validate filename
        validate_filename(request.filename)
    except FilenameValidationError as e:
        logger.warning(
            "Filename validation failed",
            extra={
                "session_id": str(session_id),
                "file_name": request.filename,
                "error": str(e),
            },
        )
        raise FilenameError(str(e), request.filename) from e

    # Generate unique S3 key
    s3_key = generate_safe_s3_key(str(session_id), request.filename)

    try:
        # Generate presigned URL
        presigned_url, expires_at = s3_client.generate_presigned_url(
            s3_key=s3_key,
            content_type=request.content_type,
        )
    except Exception as e:
        logger.exception(
            "Failed to generate presigned URL from S3",
            extra={"session_id": str(session_id), "s3_key": s3_key, "error": str(e)},
        )
        raise S3PresignError(f"Failed to generate upload URL: {str(e)}") from e

    logger.info(
        "Presigned URL generated successfully",
        extra={"session_id": str(session_id), "s3_key": s3_key},
    )

    return PresignedUrlResponse(
        presigned_url=presigned_url,
        s3_key=s3_key,
        expires_at=expires_at.isoformat(),
        content_type=request.content_type,
    )
