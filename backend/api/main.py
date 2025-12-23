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

from backend.observability.middleware import CorrelationMiddleware, LangfuseMiddleware
from .routers import (
    courses_router,
    documents_router,
    health_router,
    jobs_router,
    sessions_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Handles startup and shutdown events.
    """
    # Startup
    yield
    # Shutdown


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

    # Register all routers
    app.include_router(health_router)
    app.include_router(sessions_router)
    app.include_router(courses_router, prefix="/api/v1")
    app.include_router(documents_router)
    app.include_router(jobs_router)

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
    )
