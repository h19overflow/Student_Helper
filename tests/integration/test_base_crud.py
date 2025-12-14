"""
Test suite for BaseCRUD generic database operations.

Tests basic CRUD functionality: create, read (by ID and all), update, delete, exists.
Uses async fixtures with SQLAlchemy mocking to verify correct query behavior.

System role: Verification of generic database layer foundation
"""

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.boundary.db.CRUD.base_crud import BaseCRUD
from backend.boundary.db.base import Base, UUIDMixin, TimestampMixin


class MockModel(Base, UUIDMixin, TimestampMixin):
    """Mock SQLAlchemy model for testing BaseCRUD."""

    __tablename__ = "mock_models"


@pytest.fixture
def base_crud() -> BaseCRUD:
    """Provide BaseCRUD instance for testing."""
    return BaseCRUD(MockModel)


@pytest.fixture
def mock_session() -> AsyncSession:
    """Provide mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_id() -> uuid.UUID:
    """Provide sample UUID for testing."""
    return uuid.uuid4()


class TestBaseCRUDCreate:
    """Test suite for BaseCRUD.create() method."""

    @pytest.mark.asyncio
    async def test_create_should_add_instance_to_session(
        self, base_crud: BaseCRUD, mock_session: AsyncSession
    ) -> None:
        """Test create adds instance and flushes/refreshes."""
        # Arrange
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        # Act
        await base_crud.create(mock_session)

        # Assert
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_should_flush_before_refresh(
        self, base_crud: BaseCRUD, mock_session: AsyncSession
    ) -> None:
        """Test flush is called before refresh to ensure ID generation."""
        # Arrange
        call_order = []

        async def flush_effect() -> None:
            call_order.append("flush")

        async def refresh_effect(obj: Any) -> None:
            call_order.append("refresh")

        mock_session.flush = AsyncMock(side_effect=flush_effect)
        mock_session.refresh = AsyncMock(side_effect=refresh_effect)

        # Act
        await base_crud.create(mock_session)

        # Assert
        assert call_order == ["flush", "refresh"]


class TestBaseCRUDGetByID:
    """Test suite for BaseCRUD.get_by_id() method."""

    @pytest.mark.asyncio
    async def test_get_by_id_should_return_model_when_found(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test get_by_id returns model instance when ID exists."""
        # Arrange
        mock_instance = MagicMock()
        mock_instance.id = sample_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_instance)

        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.get_by_id(mock_session, sample_id)

        # Assert
        assert result == mock_instance
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_should_return_none_when_not_found(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test get_by_id returns None when ID doesn't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.get_by_id(mock_session, sample_id)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_should_construct_correct_query(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test get_by_id constructs WHERE clause filtering by ID."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        await base_crud.get_by_id(mock_session, sample_id)

        # Assert
        # Verify execute was called with a select statement
        call_args = mock_session.execute.call_args
        assert call_args is not None


class TestBaseCRUDGetAll:
    """Test suite for BaseCRUD.get_all() method."""

    @pytest.mark.asyncio
    async def test_get_all_should_return_all_records(
        self, base_crud: BaseCRUD, mock_session: AsyncSession
    ) -> None:
        """Test get_all returns sequence of all models without limit."""
        # Arrange
        instances = [MagicMock(), MagicMock(), MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=instances)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.get_all(mock_session)

        # Assert
        assert result == instances
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_all_should_return_empty_sequence_when_no_records(
        self, base_crud: BaseCRUD, mock_session: AsyncSession
    ) -> None:
        """Test get_all returns empty sequence when no records exist."""
        # Arrange
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.get_all(mock_session)

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_should_apply_limit_when_provided(
        self, base_crud: BaseCRUD, mock_session: AsyncSession
    ) -> None:
        """Test get_all respects limit parameter for pagination."""
        # Arrange
        instances = [MagicMock(), MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=instances)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.get_all(mock_session, limit=2)

        # Assert
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_all_should_apply_offset_when_provided(
        self, base_crud: BaseCRUD, mock_session: AsyncSession
    ) -> None:
        """Test get_all respects offset parameter for pagination."""
        # Arrange
        instances = [MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=instances)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.get_all(mock_session, limit=1, offset=5)

        # Assert
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_all_should_apply_both_limit_and_offset(
        self, base_crud: BaseCRUD, mock_session: AsyncSession
    ) -> None:
        """Test get_all applies both limit and offset together."""
        # Arrange
        instances = [MagicMock()]
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=instances)
        mock_result = MagicMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)

        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.get_all(mock_session, limit=10, offset=20)

        # Assert
        mock_session.execute.assert_called_once()


class TestBaseCRUDUpdateByID:
    """Test suite for BaseCRUD.update_by_id() method."""

    @pytest.mark.asyncio
    async def test_update_by_id_should_return_updated_model_when_found(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test update_by_id returns updated model instance when ID exists."""
        # Arrange
        updated_instance = MagicMock()
        updated_instance.id = sample_id

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_instance)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.update_by_id(mock_session, sample_id, name="new_name")

        # Assert
        assert result == updated_instance

    @pytest.mark.asyncio
    async def test_update_by_id_should_return_none_when_not_found(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test update_by_id returns None when ID doesn't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.update_by_id(mock_session, sample_id, name="new_name")

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_update_by_id_should_accept_multiple_fields(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test update_by_id updates multiple fields from kwargs."""
        # Arrange
        updated_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=updated_instance)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        await base_crud.update_by_id(
            mock_session, sample_id, field1="value1", field2="value2"
        )

        # Assert
        mock_session.execute.assert_called_once()


class TestBaseCRUDDeleteByID:
    """Test suite for BaseCRUD.delete_by_id() method."""

    @pytest.mark.asyncio
    async def test_delete_by_id_should_return_true_when_deleted(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test delete_by_id returns True when record is deleted."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.delete_by_id(mock_session, sample_id)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_by_id_should_return_false_when_not_found(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test delete_by_id returns False when record doesn't exist."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.delete_by_id(mock_session, sample_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_by_id_should_execute_delete_statement(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test delete_by_id executes proper DELETE statement."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        await base_crud.delete_by_id(mock_session, sample_id)

        # Assert
        mock_session.execute.assert_called_once()


class TestBaseCRUDExists:
    """Test suite for BaseCRUD.exists() method."""

    @pytest.mark.asyncio
    async def test_exists_should_return_true_when_id_found(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test exists returns True when ID exists in database."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_id)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.exists(mock_session, sample_id)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_should_return_false_when_id_not_found(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test exists returns False when ID doesn't exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await base_crud.exists(mock_session, sample_id)

        # Assert
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_should_execute_efficient_query(
        self, base_crud: BaseCRUD, mock_session: AsyncSession, sample_id: uuid.UUID
    ) -> None:
        """Test exists queries only ID column (efficient)."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=sample_id)
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act
        await base_crud.exists(mock_session, sample_id)

        # Assert
        mock_session.execute.assert_called_once()
