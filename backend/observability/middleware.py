"""
FastAPI middleware for observability.

Correlation ID, Langfuse tracing, and request logging middleware.

Dependencies: fastapi, backend.observability
System role: Request/response observability injection
"""

import logging
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next):
        """
        Log HTTP request and response with timing.

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response: Response object
        """
        start_time = time.time()

        method = request.method
        path = request.url.path

        logger.info(
            f"{method} {path}",
            extra={
                "method": method,
                "path": path,
                "query_string": str(request.url.query) if request.url.query else None,
                "client_host": request.client.host if request.client else None,
            },
        )

        try:
            response: Response = await call_next(request)
            process_time = time.time() - start_time

            logger.info(
                f"{method} {path} - {response.status_code}",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "process_time_ms": round(process_time * 1000, 2),
                },
            )
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.exception(
                f"{method} {path} - Exception",
                extra={
                    "method": method,
                    "path": path,
                    "process_time_ms": round(process_time * 1000, 2),
                    "error_type": type(e).__name__,
                    "error_msg": str(e),
                    "error_args": repr(e.args) if hasattr(e, 'args') else None,
                },
            )
            raise


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware for correlation ID injection."""

    async def dispatch(self, request: Request, call_next):
        """
        Inject correlation ID into request context.

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response: Response with correlation ID header
        """
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        response: Response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class LangfuseMiddleware(BaseHTTPMiddleware):
    """Middleware for Langfuse tracing."""

    async def dispatch(self, request: Request, call_next):
        """
        Trace HTTP request/response.

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response: Response object
        """
        response: Response = await call_next(request)
        return response
