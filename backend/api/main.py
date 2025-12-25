"""
FastAPI application with assembled routers.

Initializes FastAPI app with all API routers and configures uvicorn server.

Dependencies: fastapi, backend.api.routers, uvicorn
System role: API entry point with router assembly and server launch
"""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import logging
from backend.observability.middleware import CorrelationMiddleware, LangfuseMiddleware
from backend.api.deps.dependencies import get_service_cache
from .routers import (
    chat_router,
    courses_router,
    documents_router,
    health_router,
    jobs_router,
    sessions_router,
    visual_knowledge_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    logger = logging.getLogger("uvicorn")
    
    # Startup
    logger.info("Pre-warming service cache...")
    cache = get_service_cache()
    # Trigger property access to load instances
    _ = cache.vector_store
    _ = cache.rag_agent
    _ = cache.document_pipeline
    _ = cache.s3_client
    _ = cache.diagram_service
    logger.info("Service cache pre-warmed")
    
    yield
    
    # Shutdown
    cache.clear()
    logger.info("Service cache cleared")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application with routers.

    Returns:
        FastAPI: Configured application instance with all routers registered
    """
    app = FastAPI(
        title="Student Helper RAG API",
        description="Student-focused RAG application with session-based Q&A",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add observability middleware
    app.add_middleware(CorrelationMiddleware)
    app.add_middleware(LangfuseMiddleware)

    # Register all routers with /api/v1 prefix for versioning
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(sessions_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(courses_router, prefix="/api/v1")
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(visual_knowledge_router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
    )
