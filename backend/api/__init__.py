"""
API routes module.

FastAPI routers for all HTTP endpoints.
"""

from fastapi import APIRouter

from .routers import (
    diagrams_router,
    documents_router,
    health_router,
    jobs_router,
    sessions_router,
)

api_router = APIRouter()

# Include all routers
api_router.include_router(health_router)
api_router.include_router(sessions_router)
api_router.include_router(documents_router)
api_router.include_router(diagrams_router)
api_router.include_router(jobs_router)

__all__ = ["api_router"]
