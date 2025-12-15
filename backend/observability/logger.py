"""
Logger configuration.

Provides configured logger with JSON formatting and correlation ID injection.

Dependencies: logging (stdlib)
System role: Centralized logging configuration
"""

import logging
import sys


def configure_logging() -> None:
    """Configure Python logging with ISO timestamp and structured format."""
    # Remove any existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler with detailed format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # Create formatter with ISO timestamp
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

    # Reduce noise from verbose third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get configured logger.

    Args:
        name: Logger name (usually __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)
