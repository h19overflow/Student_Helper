"""
Celery workers module.

Async task processing for document ingestion and evaluation.

Dependencies: celery, backend.configs
System role: Background task processing
"""

from celery import Celery
from backend.configs import get_settings

settings = get_settings()
celery_config = settings.celery

celery_app = Celery(
    "legal_search",
    broker=celery_config.broker_url,
    backend=celery_config.result_backend_url,
)

celery_app.conf.update(
    task_serializer=celery_config.task_serializer,
    result_serializer=celery_config.result_serializer,
    accept_content=celery_config.accept_content,
    timezone=celery_config.timezone,
    task_max_retries=celery_config.task_max_retries,
)
