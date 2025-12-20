"""
S3 image uploader for visual knowledge diagrams.

Handles uploading generated images to S3 bucket with proper metadata and
MIME type detection. Returns S3 key for database storage.

Dependencies: boto3, logging, uuid, base64
System role: S3 persistence layer for visual diagrams
"""

import asyncio
import base64
import logging
from uuid import UUID, uuid4
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import boto3

logger = logging.getLogger(__name__)


class S3ImageUploader:
    """
    Uploads generated images to S3 bucket.

    Handles base64 image data, detects MIME type, and stores with proper
    S3 key structure: sessions/{session_id}/images/{image_id}.{ext}
    """

    def __init__(self, s3_client: "boto3.client", bucket_name: str) -> None:
        """
        Initialize S3 image uploader.

        Args:
            s3_client: Boto3 S3 client
            bucket_name: S3 bucket for image storage

        Raises:
            ValueError: If s3_client or bucket_name not provided
        """
        if not s3_client:
            raise ValueError("s3_client is required")
        if not bucket_name:
            raise ValueError("bucket_name is required")

        self.s3_client = s3_client
        self.bucket_name = bucket_name

        logger.debug(
            f"{__name__}:__init__ - S3ImageUploader initialized "
            f"bucket={bucket_name}"
        )

    def _detect_mime_type_and_extension(self, image_base64: str) -> tuple[str, str]:
        """
        Detect image MIME type from base64 data signature.

        Args:
            image_base64: Base64-encoded image data

        Returns:
            Tuple of (mime_type, extension) e.g., ("image/png", "png")
        """
        # Decode first few bytes to check magic numbers
        try:
            image_bytes = base64.b64decode(image_base64[:100])
        except Exception:
            logger.warning(
                f"{__name__}:_detect_mime_type_and_extension - "
                "Failed to decode base64, defaulting to PNG"
            )
            return ("image/png", "png")

        # Check magic numbers for format detection
        if image_bytes.startswith(b"\x89PNG"):
            return ("image/png", "png")
        elif image_bytes.startswith(b"\xff\xd8\xff"):
            return ("image/jpeg", "jpeg")
        elif image_bytes.startswith(b"GIF8"):
            return ("image/gif", "gif")
        elif image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:12]:
            return ("image/webp", "webp")
        else:
            # Default to PNG if detection fails
            logger.warning(
                f"{__name__}:_detect_mime_type_and_extension - "
                "Could not detect format, defaulting to PNG"
            )
            return ("image/png", "png")

    async def upload_image(
        self,
        image_base64: str,
        session_id: UUID,
    ) -> tuple[str, str]:
        """
        Upload image to S3 and return key and MIME type.

        Args:
            image_base64: Base64-encoded image data
            session_id: Session UUID for S3 path

        Returns:
            Tuple of (s3_key, mime_type)

        Raises:
            ValueError: If image_base64 or session_id not provided
            Exception: If S3 upload fails
        """
        try:
            # Validate inputs
            if not image_base64 or not image_base64.strip():
                raise ValueError("image_base64 cannot be empty")
            if not session_id:
                raise ValueError("session_id is required")

            logger.debug(
                f"{__name__}:upload_image - Detecting image format "
                f"session_id={session_id}"
            )

            # Detect MIME type and extension
            mime_type, extension = self._detect_mime_type_and_extension(
                image_base64
            )
            logger.debug(
                f"{__name__}:upload_image - Detected format: {mime_type}"
            )

            # Decode base64 to binary
            try:
                image_bytes = base64.b64decode(image_base64)
            except Exception as e:
                logger.error(
                    f"{__name__}:upload_image - Failed to decode base64: {e}"
                )
                raise ValueError(f"Invalid base64 image data: {e}")

            # Generate S3 key
            image_id = str(uuid4())
            s3_key = f"sessions/{session_id}/images/{image_id}.{extension}"

            logger.debug(
                f"{__name__}:upload_image - Uploading to S3 "
                f"s3_key={s3_key}, size={len(image_bytes)} bytes"
            )

            # Upload to S3 (wrap sync call in thread executor)
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_bytes,
                ContentType=mime_type,
                Metadata={
                    "session_id": str(session_id),
                    "image_id": image_id,
                },
            )

            logger.info(
                f"{__name__}:upload_image - Successfully uploaded "
                f"s3_key={s3_key}, mime_type={mime_type}"
            )

            return s3_key, mime_type

        except ValueError as e:
            logger.error(f"{__name__}:upload_image - ValueError: {e}")
            raise
        except Exception as e:
            logger.error(
                f"{__name__}:upload_image - {type(e).__name__}: {e}",
                exc_info=True,
            )
            raise
