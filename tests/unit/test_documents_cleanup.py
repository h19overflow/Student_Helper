"""
Unit tests for cleanup_temp_file function.

Tests temp file and directory cleanup behavior.
Dependencies: pytest, backend.api.routers.documents
System role: Cleanup function validation
"""

import logging
from pathlib import Path
import pytest
import tempfile
import shutil

from backend.api.routers.documents import cleanup_temp_file


class TestCleanupTempFile:
    """Test suite for cleanup_temp_file function."""

    def test_cleanup_existing_file(self, temp_file):
        """
        Test cleanup removes existing file.

        Arrange: Create temporary file
        Act: Call cleanup_temp_file
        Assert: File is removed
        """
        # Arrange
        assert temp_file.exists()

        # Act
        cleanup_temp_file(str(temp_file))

        # Assert
        assert not temp_file.exists()

    def test_cleanup_nonexistent_file(self):
        """
        Test cleanup handles nonexistent file gracefully.

        Arrange: Create path that doesn't exist
        Act: Call cleanup_temp_file
        Assert: No error raised
        """
        # Arrange
        nonexistent_path = Path("/tmp/nonexistent_file_12345.txt")
        assert not nonexistent_path.exists()

        # Act & Assert - should not raise
        cleanup_temp_file(str(nonexistent_path))

    def test_cleanup_removes_temp_directory(self, temp_dir):
        """
        Test cleanup removes parent studybuddy_ temp directory.

        Arrange: Create file in studybuddy_ prefixed directory
        Act: Call cleanup_temp_file
        Assert: File and directory removed
        """
        # Arrange
        test_file = temp_dir / "document.pdf"
        test_file.write_text("test content")
        assert test_file.exists()
        assert temp_dir.exists()

        # Act
        cleanup_temp_file(str(test_file))

        # Assert
        assert not test_file.exists()
        assert not temp_dir.exists()

    def test_cleanup_skips_non_studybuddy_parent_directory(self):
        """
        Test cleanup doesn't remove parent dir if not prefixed with studybuddy_.

        Arrange: Create file in non-studybuddy temp directory
        Act: Call cleanup_temp_file
        Assert: File removed but directory preserved
        """
        # Arrange
        temp_dir = Path(tempfile.mkdtemp(prefix="other_"))
        test_file = temp_dir / "document.pdf"
        test_file.write_text("test content")
        assert test_file.exists()
        assert temp_dir.exists()

        # Act
        cleanup_temp_file(str(test_file))

        # Assert
        assert not test_file.exists()
        assert temp_dir.exists()  # Directory should remain

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_cleanup_handles_permission_errors_gracefully(self):
        """
        Test cleanup handles errors gracefully without raising exceptions.

        Arrange: Call cleanup on non-existent path
        Act: Call cleanup_temp_file
        Assert: No exception raised (errors logged internally)
        """
        # This should not raise any exception
        cleanup_temp_file("/restricted/path/that/does/not/exist.txt")
        # Success - no exception

    def test_cleanup_logs_success_for_file_removal(self, temp_file, caplog):
        """
        Test cleanup logs debug message on successful file removal.

        Arrange: Create temporary file
        Act: Call cleanup_temp_file with logging enabled
        Assert: Debug log message recorded
        """
        # Arrange
        with caplog.at_level(logging.DEBUG):
            # Act
            cleanup_temp_file(str(temp_file))

        # Assert
        assert "Cleaned up temp file" in caplog.text

    def test_cleanup_logs_success_for_directory_removal(self, temp_dir, caplog):
        """
        Test cleanup logs debug message on successful directory removal.

        Arrange: Create temp directory with studybuddy_ prefix
        Act: Call cleanup_temp_file with logging enabled
        Assert: Directory removal logged
        """
        # Arrange
        test_file = temp_dir / "document.pdf"
        test_file.write_text("test")

        with caplog.at_level(logging.DEBUG):
            # Act
            cleanup_temp_file(str(test_file))

        # Assert
        assert "Cleaned up temp directory" in caplog.text

    def test_cleanup_with_multiple_files_in_directory(self, temp_dir):
        """
        Test cleanup removes directory even with multiple files.

        Arrange: Create multiple files in temp directory
        Act: Call cleanup_temp_file on one file
        Assert: All files and directory removed via rmtree
        """
        # Arrange
        file1 = temp_dir / "file1.pdf"
        file2 = temp_dir / "file2.pdf"
        file1.write_text("content1")
        file2.write_text("content2")
        assert file1.exists() and file2.exists()

        # Act
        cleanup_temp_file(str(file1))

        # Assert
        assert not file1.exists()
        assert not file2.exists()
        assert not temp_dir.exists()

    def test_cleanup_idempotent(self, temp_file):
        """
        Test cleanup can be called multiple times safely.

        Arrange: Create temp file
        Act: Call cleanup_temp_file twice
        Assert: No error on second call
        """
        # Arrange
        file_path = str(temp_file)

        # Act
        cleanup_temp_file(file_path)
        # Second call should not raise
        cleanup_temp_file(file_path)

        # Assert
        assert not Path(file_path).exists()

    def test_cleanup_with_various_file_extensions(self):
        """
        Test cleanup works with various file extensions.

        Arrange: Create temp dir with files of different types
        Act: Call cleanup_temp_file on each
        Assert: All removed successfully
        """
        # Arrange
        temp_base = Path(tempfile.mkdtemp(prefix="studybuddy_"))
        extensions = [".pdf", ".doc", ".docx", ".txt", ".md"]

        try:
            for ext in extensions:
                # Create fresh dir for each file to test independently
                temp_dir = Path(tempfile.mkdtemp(prefix="studybuddy_"))
                test_file = temp_dir / f"document{ext}"
                test_file.write_text("content")

                # Act
                cleanup_temp_file(str(test_file))

                # Assert
                assert not test_file.exists()
                assert not temp_dir.exists()
        finally:
            # Final cleanup
            if temp_base.exists():
                shutil.rmtree(temp_base, ignore_errors=True)

    def test_cleanup_with_special_characters_in_filename(self):
        """
        Test cleanup handles filenames with special characters.

        Arrange: Create file with special chars in name
        Act: Call cleanup_temp_file
        Assert: File removed successfully
        """
        # Arrange
        temp_dir = Path(tempfile.mkdtemp(prefix="studybuddy_"))
        special_file = temp_dir / "document (1) [FINAL].pdf"
        special_file.write_text("content")
        assert special_file.exists()

        # Act
        cleanup_temp_file(str(special_file))

        # Assert
        assert not special_file.exists()
        assert not temp_dir.exists()
