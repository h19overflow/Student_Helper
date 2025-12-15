"""
Shared test fixtures and configuration for entire test suite.

Provides: Database session mocks, service mocks, async fixtures, temp file cleanup
Dependencies: pytest, sqlalchemy, fastapi
System role: Test infrastructure and fixture management
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_async_db():
    """
    Create in-memory SQLite async database for testing.

    Yields:
        AsyncSession: Test database session with cleanup (lazy imported to avoid settings issues)
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy.pool import StaticPool
    from backend.boundary.db.base import Base

    # Use SQLite in-memory database for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create session for test
    async with async_session() as session:
        yield session
        await session.rollback()

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
def mock_job_service():
    """
    Create mock JobService for testing.

    Returns:
        MagicMock: Mocked JobService with async methods
    """
    service = AsyncMock()
    service.create_job = AsyncMock(return_value=uuid.uuid4())
    service.mark_job_running = AsyncMock()
    service.mark_job_completed = AsyncMock()
    service.mark_job_failed = AsyncMock()
    service.get_job = AsyncMock()
    service.db = AsyncMock()
    service.db.commit = AsyncMock()
    service.db.rollback = AsyncMock()
    return service


@pytest.fixture
def mock_document_service():
    """
    Create mock DocumentService for testing.

    Returns:
        MagicMock: Mocked DocumentService with async methods
    """
    service = AsyncMock()
    service.upload_document = AsyncMock(return_value=MagicMock(
        document_id=uuid.uuid4(),
        chunk_count=5,
        processing_time_ms=1000,
        index_path=".faiss_index",
    ))
    service.get_session_documents = AsyncMock(return_value=[])
    service.db = AsyncMock()
    return service


@pytest.fixture
def temp_file():
    """
    Create a temporary file for testing file uploads.

    Yields:
        Path: Path to temporary file
    """
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        temp_path = Path(f.name)
        f.write(b"test content")

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_pdf_file():
    """
    Create a temporary PDF-like file for testing.

    Yields:
        Path: Path to temporary PDF file
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        temp_path = Path(f.name)
        # Write minimal PDF header for testing
        f.write(b"%PDF-1.4\n")
        f.write(b"1 0 obj\n<< >>\nendobj\n")

    yield temp_path

    # Cleanup
    if temp_path.exists():
        temp_path.unlink()


@pytest.fixture
def temp_dir():
    """
    Create a temporary directory for test files.

    Yields:
        Path: Path to temporary directory
    """
    temp_path = Path(tempfile.mkdtemp(prefix="studybuddy_test_"))
    yield temp_path

    # Cleanup
    import shutil
    if temp_path.exists():
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_upload_file():
    """
    Create a mock UploadFile object for testing.

    Returns:
        MagicMock: Mock UploadFile with filename and read method
    """
    mock_file = MagicMock()
    mock_file.filename = "test_document.pdf"
    mock_file.read = AsyncMock(return_value=b"%PDF-1.4\ntest content")
    mock_file.file = MagicMock()
    mock_file.file.seek = MagicMock()
    return mock_file


@pytest.fixture
def session_id():
    """Generate a test session ID."""
    return uuid.uuid4()


@pytest.fixture
def job_id():
    """Generate a test job ID."""
    return uuid.uuid4()


@pytest.fixture
def task_id():
    """Generate a test task ID."""
    return str(uuid.uuid4())
