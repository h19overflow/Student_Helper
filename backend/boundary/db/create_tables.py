"""
Database table creation script.

Creates all tables defined in ORM models using SQLAlchemy metadata.

Dependencies: sqlalchemy, backend.configs
System role: Database schema initialization

Usage:
    python -m backend.boundary.db.create_tables
"""

from backend.boundary.db.base import Base
from backend.boundary.db.connection import get_engine
from backend.boundary.db.CRUD.chat_history_crud import ChatHistoryCRUD

# Import all models to register them with Base.metadata
from backend.boundary.db.models.course_model import CourseModel  # noqa: F401
from backend.boundary.db.models.session_model import SessionModel  # noqa: F401
from backend.boundary.db.models.document_model import DocumentModel  # noqa: F401
from backend.boundary.db.models.job_model import JobModel  # noqa: F401
from backend.boundary.db.models.image_model import ImageModel  # noqa: F401


def create_all_tables() -> None:
    """
    Create all database tables from registered ORM models.

    Idempotent: calls CREATE TABLE IF NOT EXISTS for each model, so safe
    to run multiple times. Existing tables remain unchanged.

    Creates both SQLAlchemy tables (sessions, documents, jobs) and
    chat_messages table (via PostgresChatMessageHistory).

    Raises:
        SQLAlchemyError: If database connection fails or table creation fails
        (e.g., invalid schema, permissions denied, unsupported data types)

    Usage:
        python -m backend.boundary.db.create_tables
        # Or in code:
        create_all_tables()
    """
    engine = get_engine()

    # Create SQLAlchemy ORM tables
    Base.metadata.create_all(bind=engine)
    print("SQLAlchemy tables created successfully.")

    # Create chat_messages table (via langchain_postgres)
    ChatHistoryCRUD.create_table()
    print("Chat history table created successfully.")

    print("All tables created successfully.")


def drop_all_tables() -> None:
    """
    Drop all database tables and their data.

    WARNING: Irreversible data loss. Only use in development environments.
    Deletes all rows in all tables registered with Base.metadata.

    Raises:
        SQLAlchemyError: If database connection fails or drop fails
        (e.g., cascading foreign keys prevent deletion, permissions denied)

    Usage:
        # In development only:
        from backend.boundary.db.create_tables import drop_all_tables, create_all_tables
        drop_all_tables()
        create_all_tables()  # Reinitialize clean database
    """
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped successfully.")


if __name__ == "__main__":
    create_all_tables()
