"""
S3 Documents bucket configuration.

Settings for raw document storage bucket and presigned URL generation.

Dependencies: pydantic_settings
System role: S3 documents bucket configuration
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class S3DocumentsSettings(BaseSettings):
    """Settings for S3 documents bucket operations."""

    model_config = SettingsConfigDict(
        env_prefix="S3_DOCUMENTS_",
        case_sensitive=False,
        extra="ignore",
    )

    bucket: str = Field(
        default="student-helper-dev-documents",
        description="S3 bucket for raw document storage",
    )
    region: str = Field(
        default="ap-southeast-2",
        description="AWS region for S3 bucket",
    )
    presigned_url_expiry: int = Field(
        default=3600,
        description="Presigned URL expiry in seconds (default 1 hour)",
    )
