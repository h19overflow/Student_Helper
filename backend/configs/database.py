"""
Database configuration settings.

Manages PostgreSQL connection parameters for SQLAlchemy.
Supports connection pooling and async operations.

Dependencies: pydantic, pydantic_settings
System role: Database connection configuration for ORM
"""

from pydantic import Field
from pydantic_settings import SettingsConfigDict

from backend.configs.base import BaseSettings


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="POSTGRES_",
        case_sensitive=False,
        extra="ignore",
    )

    host: str = Field(default="localhost", description="PostgreSQL host")
    port: int = Field(default=5432, description="PostgreSQL port")
    user: str = Field(default="postgres", description="PostgreSQL user")
    password: str = Field(default="postgres", description="PostgreSQL password")
    db: str = Field(default="studenthelper", description="PostgreSQL database name")

    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum overflow connections")
    pool_timeout: int = Field(default=30, description="Connection pool timeout in seconds")
    echo_sql: bool = Field(default=False, description="Echo SQL statements to logs")

    sslmode: str = Field(default="require", description="SSL mode for RDS connections")

    @property
    def database_url(self) -> str:
        """
        Construct PostgreSQL connection URL.

        Returns:
            str: SQLAlchemy-compatible database URL
        """
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}?sslmode={self.sslmode}"
        )

    @property
    def async_database_url(self) -> str:
        """
        Construct async PostgreSQL connection URL.

        Returns:
            str: SQLAlchemy async-compatible database URL (asyncpg uses 'ssl' param)
        """
        ssl_param = "ssl=require" if self.sslmode == "require" else ""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.db}?{ssl_param}"
        )
