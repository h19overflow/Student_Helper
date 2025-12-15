"""
Logging utilities for safe structured logging.

Provides helpers for safe logging without string concatenation errors.

Dependencies: logging (stdlib)
System role: Logging helper functions
"""

import logging
from typing import Any


def safe_log_value(value: Any, max_length: int = 500) -> str:
    """
    Safely convert any value to a string for logging.

    Handles lists, dicts, None, and other types safely.

    Args:
        value: Value to convert
        max_length: Maximum length before truncating

    Returns:
        str: Safe string representation
    """
    try:
        if value is None:
            return "None"
        if isinstance(value, str):
            val_str = value
        elif isinstance(value, (list, tuple)):
            val_str = f"{type(value).__name__}({len(value)} items)"
        elif isinstance(value, dict):
            val_str = f"dict({len(value)} keys)"
        else:
            val_str = str(value)

        if len(val_str) > max_length:
            return val_str[:max_length] + f"... (truncated, {len(val_str)} total)"
        return val_str
    except Exception as e:
        return f"<unable to log: {type(e).__name__}>"


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context,
) -> None:
    """
    Log a message with structured context, safely converting all values.

    Args:
        logger: Logger instance
        level: Log level (logging.INFO, etc.)
        message: Log message
        **context: Context dict with arbitrary key-value pairs
    """
    safe_context = {
        key: safe_log_value(val) for key, val in context.items()
    }
    logger.log(level, message, extra=safe_context)


def log_exception_with_context(
    logger: logging.Logger,
    message: str,
    exc: Exception,
    **context,
) -> None:
    """
    Log an exception with full context.

    Args:
        logger: Logger instance
        message: Log message
        exc: Exception instance
        **context: Additional context dict
    """
    safe_context = {
        key: safe_log_value(val) for key, val in context.items()
    }
    safe_context.update({
        "error_type": type(exc).__name__,
        "error_msg": str(exc),
    })
    logger.exception(message, extra=safe_context)
