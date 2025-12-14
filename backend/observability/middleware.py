"""
FastAPI middleware for observability.

Correlation ID and Langfuse tracing middleware.

Dependencies: fastapi, backend.observability
System role: Request/response observability injection
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import uuid


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
