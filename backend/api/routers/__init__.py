"""API routers."""

from .diagrams import router as diagrams_router
from .documents import router as documents_router
from .health import router as health_router
from .jobs import router as jobs_router
from .sessions import router as sessions_router

__all__ = [
    "diagrams_router",
    "documents_router",
    "health_router",
    "jobs_router",
    "sessions_router",
]
