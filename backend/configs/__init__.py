"""
Configuration management module.

Provides centralized, type-safe configuration using Pydantic Settings.
All config modules support environment variable mapping with validation.
"""

from backend.configs.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
