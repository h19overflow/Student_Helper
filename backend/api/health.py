"""
Health check API endpoints.

Routes: GET /health, GET /health/db, GET /health/vector-store

Dependencies: backend.boundary
System role: Health check HTTP API
"""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Basic health check."""
    pass


@router.get("/db")
async def health_check_db():
    """Database health check."""
    pass


@router.get("/vector-store")
async def health_check_vector_store():
    """Vector store health check."""
    pass
