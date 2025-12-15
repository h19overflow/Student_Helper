"""
Router utility functions.

Contains helper functions extracted from router endpoints to keep them clean.
"""

from backend.api.routers.router_utils.document_utils import (
    cleanup_temp_file,
    process_document_background,
)

__all__ = [
    "cleanup_temp_file",
    "process_document_background",
]
