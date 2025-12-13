"""
Database connection management.

Provides SQLAlchemy engine, session factory, and FastAPI dependency
for database session injection.

Dependencies: sqlalchemy, backend.configs
System role: Database connection lifecycle management
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from backend.configs import get_settings


def get_engine():
    """
    Create SQLAlchemy engine with connection pooling.

    Returns:
        Engine: Configured SQLAlchemy engine

    Usage:
        engine = get_engine()
    """
    settings = get_settings()
    db_config = settings.database

    return create_engine(
        db_config.database_url,
        echo=db_config.echo_sql,
        poolclass=QueuePool,
        pool_size=db_config.pool_size,
        max_overflow=db_config.max_overflow,
        pool_timeout=db_config.pool_timeout,
        pool_pre_ping=True,  # Verify connections before using
    )


def get_session_factory() -> sessionmaker:
    """
    Create session factory for database operations.

    Returns:
        sessionmaker: SQLAlchemy session factory

    Usage:
        SessionFactory = get_session_factory()
        with SessionFactory() as session:
            # perform database operations
    """
    engine = get_engine()
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session injection.

    Yields database session and ensures proper cleanup.
    Use as a dependency in FastAPI route handlers.

    Yields:
        Session: SQLAlchemy database session

    Usage:
        @app.get("/")
        def route(db: Session = Depends(get_db)):
            # use db session
    """
    SessionFactory = get_session_factory()
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()
