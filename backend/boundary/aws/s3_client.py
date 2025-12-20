"""
S3 client for document bucket operations.

Handles presigned URL generation for direct browser uploads.
Does NOT handle downloads - that's handled by S3DownloadTask in the pipeline.

Dependencies: boto3
System role: API-level S3 operations for presigned URLs
"""

from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError


class S3DocumentClient:
    """S3 client for document bucket operations (presigned URLs only)."""

    def __init__(self, bucket: str, region: str = "ap-southeast-2") -> None:
        """
        Initialize S3 client for document bucket.

        Args:
            bucket: S3 bucket name for document storage
            region: AWS region for S3 bucket
        """
        self._bucket = bucket
        self._region = region
        self._s3_client = boto3.client("s3", region_name=region)

    def generate_presigned_url(
        self,
        s3_key: str,
        content_type: str = "application/octet-stream",
        expires_in: int = 3600,
    ) -> tuple[str, datetime]:
        """
        Generate presigned URL for uploading a document.

        Args:
            s3_key: S3 object key (path in bucket)
            content_type: MIME type of the file
            expires_in: URL expiry in seconds (default 1 hour)

        Returns:
            tuple[str, datetime]: (presigned_url, expires_at)

        Raises:
            ClientError: If presigned URL generation fails
        """
        presigned_url = self._s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self._bucket,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        return presigned_url, expires_at

    def generate_presigned_download_url(
        self,
        s3_key: str,
        expires_in: int = 3600,
    ) -> tuple[str, datetime]:
        """
        Generate presigned URL for downloading/viewing an S3 object.

        Args:
            s3_key: S3 object key (path in bucket)
            expires_in: URL expiry in seconds (default 1 hour)

        Returns:
            tuple[str, datetime]: (presigned_url, expires_at)

        Raises:
            ClientError: If presigned URL generation fails
        """
        presigned_url = self._s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self._bucket,
                "Key": s3_key,
            },
            ExpiresIn=expires_in,
        )
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        return presigned_url, expires_at

    def file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            s3_key: S3 object key to check

        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            self._s3_client.head_object(Bucket=self._bucket, Key=s3_key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise
