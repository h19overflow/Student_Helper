"""
Base configuration settings.

Provides common configuration inherited by all specific config modules.
Handles environment detection and shared defaults.

Dependencies: pydantic_settings
System role: Foundation for all configuration classes
"""

from pydantic_settings import BaseSettings as PydanticBaseSettings, SettingsConfigDict
from pydantic import Field


class BaseSettings(PydanticBaseSettings):
    """Base configuration class with common settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = Field(
        default="development",
        description="Application environment (development, staging, production)",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode",
    )
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
