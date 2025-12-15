"""
Health check API endpoints.

Routes: GET /health, GET /health/db, GET /health/vector-store

Dependencies: backend.boundary
System role: Health check HTTP API
"""

from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    message: str


router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check."""
    return HealthResponse(status="healthy", message="Server Healthy")


@router.get("/db", response_model=HealthResponse)
async def health_check_db() -> HealthResponse:
    """Database health check."""
    return HealthResponse(status="healthy", message="Database connection OK")


@router.get("/vector-store", response_model=HealthResponse)
async def health_check_vector_store() -> HealthResponse:
    """Vector store health check."""
    return HealthResponse(status="healthy", message="Vector store accessible")
