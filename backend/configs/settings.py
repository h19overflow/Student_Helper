"""
Unified application settings.

Aggregates all configuration modules into a single Settings class.
Provides dependency injection factory for FastAPI.

Dependencies: All config modules
System role: Central configuration aggregator for the application
"""

from functools import lru_cache

from backend.configs.base import BaseSettings
from backend.configs.database import DatabaseSettings
from backend.configs.vector_store import VectorStoreSettings
from backend.configs.observability import ObservabilitySettings
from backend.configs.s3_documents import S3DocumentsSettings


class Settings(BaseSettings):
    """Unified application settings aggregating all config modules."""

    # Aggregated settings
    database: DatabaseSettings = DatabaseSettings()
    vector_store: VectorStoreSettings = VectorStoreSettings()
    observability: ObservabilitySettings = ObservabilitySettings()
    s3_documents: S3DocumentsSettings = S3DocumentsSettings()


@lru_cache
def get_settings() -> Settings:
    """
    Get application settings singleton.

    Returns Settings instance, cached for dependency injection.
    Environment variables loaded once at startup.

    Returns:
        Settings: Application settings instance

    Usage:
        from backend.configs import get_settings
        settings = get_settings()
    """
    return Settings()
