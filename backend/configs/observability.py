"""
Observability configuration settings.

Settings for Langfuse tracing, logging, and metrics collection.

Dependencies: pydantic_settings
System role: Observability configuration for tracing and logging
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class ObservabilitySettings(BaseSettings):
    """Observability configuration for Langfuse and logging."""

    langfuse_public_key: str | None = Field(
        default=None,
        description="Langfuse public key for tracing",
    )
    langfuse_secret_key: str | None = Field(
        default=None,
        description="Langfuse secret key for tracing",
    )
    langfuse_host: str = Field(
        default="http://localhost:3000",
        description="Langfuse server host URL",
    )
    enable_tracing: bool = Field(
        default=True,
        description="Enable Langfuse tracing",
    )

    class Config:
        """Pydantic config for environment variable loading."""

        env_prefix = "LANGFUSE_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
