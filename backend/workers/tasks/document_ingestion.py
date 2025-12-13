"""
Document ingestion Celery task.

Async task: ingest_document(session_id, doc_id, file_url)
Flow: fetch -> parse -> chunk -> embed -> upsert -> update status

Dependencies: backend.application, backend.boundary, backend.workers
System role: Async document processing task
"""

from backend.workers import celery_app
import uuid


@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_backoff_max=600,
)
def ingest_document(self, session_id: str, doc_id: str, file_url: str):
    """
    Ingest document asynchronously.

    Args:
        session_id: Session UUID as string
        doc_id: Document UUID as string
        file_url: URL or path to document file

    Returns:
        dict: Ingestion result with chunk count and status
    """
    pass
