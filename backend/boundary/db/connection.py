"""
Database connection management.

Provides SQLAlchemy engine, session factory, and FastAPI dependency
for database session injection.

Dependencies: sqlalchemy, backend.configs
System role: Database connection lifecycle management
"""

from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker

from backend.configs import get_settings


def get_engine():
    """
    Create SQLAlchemy engine with connection pooling and health checks.

    Configures QueuePool for efficient connection reuse. pool_pre_ping=True
    verifies connections before use to detect stale/broken connections early.

    Returns:
        Engine: Configured SQLAlchemy engine with active pooling

    Raises:
        ArgumentError: If database URL is invalid or engine creation fails

    Usage:
        engine = get_engine()
        engine.execute("SELECT 1")  # Test connection
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

    Returns fresh sessionmaker bound to engine with autocommit=False and
    autoflush=False for explicit transaction control and predictable behavior.

    Returns:
        sessionmaker: Session factory configured for manual transaction control

    Usage:
        SessionFactory = get_session_factory()
        session = SessionFactory()
        try:
            session.add(obj)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    """
    engine = get_engine()
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session injection with automatic cleanup.

    Creates a new database session for each request and ensures it's closed
    after the route completes, even if exceptions occur. Use this for any
    route that needs database access.

    Yields:
        Session: SQLAlchemy database session (scoped to request lifetime)

    Raises:
        SQLAlchemyError: Propagated from database operations

    Usage:
        from fastapi import Depends

        @app.get("/sessions/{id}")
        async def get_session(id: str, db: Session = Depends(get_db)):
            return db.query(SessionModel).filter(SessionModel.id == id).first()
    """
    SessionFactory = get_session_factory()
    db = SessionFactory()
    try:
        yield db
    finally:
        db.close()


def get_async_engine() -> AsyncEngine:
    """
    Create async SQLAlchemy engine with connection pooling.

    Configures QueuePool for efficient connection reuse. pool_pre_ping=True
    verifies connections before use to detect stale/broken connections early.

    Returns:
        AsyncEngine: Configured async SQLAlchemy engine

    Raises:
        ArgumentError: If database URL is invalid or engine creation fails

    Usage:
        engine = get_async_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
    """
    settings = get_settings()
    db_config = settings.database

    return create_async_engine(
        db_config.async_database_url,
        echo=db_config.echo_sql,
        poolclass=QueuePool,
        pool_size=db_config.pool_size,
        max_overflow=db_config.max_overflow,
        pool_timeout=db_config.pool_timeout,
        pool_pre_ping=True,
    )


def get_async_session_factory() -> async_sessionmaker:
    """
    Create async session factory for database operations.

    Returns fresh async_sessionmaker bound to engine with autocommit=False and
    autoflush=False for explicit transaction control and predictable behavior.

    Returns:
        async_sessionmaker: Async session factory configured for manual transaction control

    Usage:
        SessionFactory = get_async_session_factory()
        async with SessionFactory() as session:
            session.add(obj)
            await session.commit()
    """
    engine = get_async_engine()
    return async_sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for async database session injection with automatic cleanup.

    Creates a new async database session for each request and ensures it's closed
    after the route completes, even if exceptions occur. Use this for any
    route that needs async database access.

    Yields:
        AsyncSession: Async SQLAlchemy database session (scoped to request lifetime)

    Raises:
        SQLAlchemyError: Propagated from database operations

    Usage:
        from fastapi import Depends

        @app.get("/sessions/{id}")
        async def get_session(id: str, db: AsyncSession = Depends(get_async_db)):
            return await session_crud.get_by_id(db, id)
    """
    SessionFactory = get_async_session_factory()
    async with SessionFactory() as session:
        yield session
