"""
Observability configuration settings.

Manages Langfuse tracing and structured logging configuration.
Includes correlation ID settings and trace sampling.

Dependencies: pydantic, pydantic_settings
System role: Observability and tracing configuration for monitoring
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class ObservabilitySettings(BaseSettings):
    """Langfuse and logging configuration."""

    # Langfuse settings
    langfuse_host: str = Field(
        default="http://localhost:3000",
        description="Langfuse server host",
    )
    langfuse_public_key: str = Field(default="", description="Langfuse public key")
    langfuse_secret_key: str = Field(default="", description="Langfuse secret key")
    langfuse_enabled: bool = Field(default=True, description="Enable Langfuse tracing")
    langfuse_sample_rate: float = Field(
        default=1.0,
        description="Trace sampling rate (0.0-1.0)",
    )

    # Logging settings
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_correlation_enabled: bool = Field(
        default=True,
        description="Enable correlation ID tracking",
    )
    log_include_timestamp: bool = Field(
        default=True,
        description="Include timestamp in logs",
    )
    log_include_caller: bool = Field(
        default=False,
        description="Include caller info in logs",
    )

    class Config:
        """Pydantic config."""

        env_prefix = "OBSERVABILITY_"
        case_sensitive = False
