"""Shared pytest fixtures for all tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_directory() -> str:
    """Create temporary directory that persists for test duration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_google_api_key() -> str:
    """Provide mock Google API key for testing."""
    return "test-api-key-12345"


@pytest.fixture
def sample_document() -> dict:
    """Provide sample document for testing."""
    return {
        "source": "/path/to/document.pdf",
        "page": 1,
    }


@pytest.fixture
def sample_content() -> str:
    """Provide sample text content for testing."""
    return """
    Introduction to Legal Systems

    A legal system is a system for interpreting and enforcing the law.
    Different jurisdictions have different legal systems. The main types
    include common law, civil law, and religious law systems.

    Common Law Systems

    Common law systems are found in the United Kingdom and former British colonies.
    They rely on judicial precedent and case law. The courts play a significant role
    in interpreting the law through their decisions.

    Civil Law Systems

    Civil law systems are found in most European countries and Latin America.
    They rely primarily on statutory law and codes rather than case law.
    """
