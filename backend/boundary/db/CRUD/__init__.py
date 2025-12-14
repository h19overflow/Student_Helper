"""
CRUD operations for database models.

Exports base CRUD class and model-specific CRUD implementations
with pre-instantiated singletons for direct use.

Usage:
    from backend.boundary.db.CRUD import session_crud, document_crud, job_crud

    # Use singleton instances
    session = await session_crud.get_by_id(db, session_id)

    # Or instantiate classes directly for custom behavior
    from backend.boundary.db.CRUD import SessionCRUD
    custom_crud = SessionCRUD()
"""

from backend.boundary.db.CRUD.base_crud import BaseCRUD
from backend.boundary.db.CRUD.session_crud import SessionCRUD, session_crud
from backend.boundary.db.CRUD.document_crud import DocumentCRUD, document_crud
from backend.boundary.db.CRUD.job_crud import JobCRUD, job_crud

__all__ = [
    "BaseCRUD",
    "SessionCRUD",
    "session_crud",
    "DocumentCRUD",
    "document_crud",
    "JobCRUD",
    "job_crud",
]
