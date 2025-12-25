"""API routers."""

from .chat import router as chat_router
from .courses import router as courses_router  # Now imports from courses/ package
from .documents import router as documents_router  # Now imports from documents/ package
from .health import router as health_router
from .jobs import router as jobs_router
from .sessions import router as sessions_router
from .visual_knowledge import router as visual_knowledge_router

__all__ = [
    "chat_router",
    "courses_router",
    "documents_router",
    "health_router",
    "jobs_router",
    "sessions_router",
    "visual_knowledge_router",
]
