"""
Celery configuration settings.

Manages Celery broker and result backend configuration for async task processing.
Includes retry policies and worker settings.

Dependencies: pydantic, pydantic_settings
System role: Async task queue configuration for document ingestion
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class CelerySettings(BaseSettings):
    """Celery and RabbitMQ configuration."""

    broker_host: str = Field(default="localhost", description="RabbitMQ host")
    broker_port: int = Field(default=5672, description="RabbitMQ port")
    broker_user: str = Field(default="guest", description="RabbitMQ user")
    broker_password: str = Field(default="guest", description="RabbitMQ password")
    broker_vhost: str = Field(default="/", description="RabbitMQ virtual host")

    result_backend_host: str = Field(default="localhost", description="Redis host for results")
    result_backend_port: int = Field(default=6379, description="Redis port")
    result_backend_db: int = Field(default=0, description="Redis database number")

    task_serializer: str = Field(default="json", description="Task serialization format")
    result_serializer: str = Field(default="json", description="Result serialization format")
    accept_content: list[str] = Field(
        default=["json"],
        description="Accepted content types",
    )
    timezone: str = Field(default="UTC", description="Celery timezone")

    # Retry policy
    task_max_retries: int = Field(default=3, description="Maximum task retry attempts")
    task_retry_backoff: int = Field(default=60, description="Retry backoff base in seconds")
    task_retry_backoff_max: int = Field(
        default=600,
        description="Maximum retry backoff in seconds",
    )

    @property
    def broker_url(self) -> str:
        """
        Construct RabbitMQ broker URL.

        Returns:
            str: Celery-compatible broker URL
        """
        return (
            f"amqp://{self.broker_user}:{self.broker_password}"
            f"@{self.broker_host}:{self.broker_port}/{self.broker_vhost}"
        )

    @property
    def result_backend_url(self) -> str:
        """
        Construct Redis result backend URL.

        Returns:
            str: Celery-compatible result backend URL
        """
        return f"redis://{self.result_backend_host}:{self.result_backend_port}/{self.result_backend_db}"

    class Config:
        """Pydantic config."""

        env_prefix = "CELERY_"
        case_sensitive = False
