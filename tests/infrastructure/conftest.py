"""Pytest fixtures for infrastructure tests."""

import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def add_iac_to_path():
    """Add IAC directory to Python path for imports."""
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    yield
    # Cleanup
    sys.path.remove(str(project_root))


@pytest.fixture
def iac_project_root():
    """Return the IAC project root directory."""
    return Path(__file__).parent.parent.parent / "IAC"


@pytest.fixture
def python_files_in_iac(iac_project_root):
    """Return all Python files in IAC directory."""
    return [f for f in iac_project_root.rglob("*.py") if "__pycache__" not in str(f)]
