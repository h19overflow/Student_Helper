"""
S3 document download task.

Downloads documents from S3 to local temp directory for processing.
Lambda-compatible: uses /tmp directory.

Dependencies: boto3
System role: First stage of document ingestion pipeline (S3 source)
"""

import os
import tempfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


class S3DownloadError(Exception):
    """Raised when S3 download fails."""

    def __init__(self, message: str, s3_key: str | None = None) -> None:
        self.s3_key = s3_key
        super().__init__(message)


class S3DownloadTask:
    """Download documents from S3 to local temp directory."""

    def __init__(self, bucket: str, region: str = "ap-southeast-2") -> None:
        """
        Initialize S3 download task.

        Args:
            bucket: S3 bucket name for document storage
            region: AWS region for S3 bucket
        """
        self._bucket = bucket
        self._region = region
        self._s3_client = boto3.client("s3", region_name=region)

    def download(self, s3_key: str) -> str:
        """
        Download document from S3 to temp directory.

        Args:
            s3_key: S3 object key (e.g., "sessions/uuid/documents/file.pdf")

        Returns:
            str: Local file path to downloaded document

        Raises:
            S3DownloadError: When download fails
        """
        if not s3_key:
            raise S3DownloadError("S3 key is required", s3_key)

        # Extract filename from s3_key
        filename = Path(s3_key).name
        if not filename:
            raise S3DownloadError(f"Invalid S3 key: {s3_key}", s3_key)

        # Create temp directory (Lambda uses /tmp)
        temp_dir = tempfile.mkdtemp(prefix="doc_pipeline_")
        local_path = os.path.join(temp_dir, filename)

        try:
            self._s3_client.download_file(
                Bucket=self._bucket,
                Key=s3_key,
                Filename=local_path,
            )
            return local_path

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "404" or error_code == "NoSuchKey":
                raise S3DownloadError(
                    f"File not found in S3: {s3_key}", s3_key
                ) from e
            raise S3DownloadError(
                f"Failed to download from S3: {e}", s3_key
            ) from e
        except Exception as e:
            raise S3DownloadError(
                f"Unexpected error downloading from S3: {e}", s3_key
            ) from e
