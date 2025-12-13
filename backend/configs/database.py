"""
Database configuration settings.

Manages PostgreSQL connection parameters for SQLAlchemy.
Supports connection pooling and async operations.

Dependencies: pydantic, pydantic_settings
System role: Database connection configuration for ORM
"""

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """PostgreSQL database configuration."""

    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(default="postgres", description="PostgreSQL password")
    postgres_db: str = Field(default="legal_search", description="PostgreSQL database name")

    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum overflow connections")
    pool_timeout: int = Field(default=30, description="Connection pool timeout in seconds")
    echo_sql: bool = Field(default=False, description="Echo SQL statements to logs")

    @property
    def database_url(self) -> str:
        """
        Construct PostgreSQL connection URL.

        Returns:
            str: SQLAlchemy-compatible database URL
        """
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def async_database_url(self) -> str:
        """
        Construct async PostgreSQL connection URL.

        Returns:
            str: SQLAlchemy async-compatible database URL
        """
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        """Pydantic config."""

        env_prefix = "POSTGRES_"
        case_sensitive = False
