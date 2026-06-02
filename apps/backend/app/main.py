"""
FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.backend.app.core.config import get_settings
from apps.backend.app.routes.v1 import router as v1_router
from apps.backend.infrastructure.db import close_sqlite_store
from apps.backend.infrastructure.db.connection import (
    close_db,
    initialize_schema,
)
from apps.backend.infrastructure.db.repository_factory import use_surrealdb

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    logger = structlog.get_logger(__name__)
    logger.info("Starting", service=settings.project_name)

    if use_surrealdb():
        try:
            await initialize_schema()
            logger.info("SurrealDB initialized")
        except Exception as e:
            logger.error("Database initialization failed", error=str(e))
            logger.warning("Application will start without database")
    else:
        settings.sqlite_db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Using local SQLite database", path=str(settings.sqlite_db_path))

    yield

    # Shutdown
    logger.info("Shutting down")
    if use_surrealdb():
        await close_db()
    else:
        close_sqlite_store()


def create_application() -> FastAPI:
    """Create FastAPI application"""
    app = FastAPI(
        title="Reverse Muse",
        description="AI-powered reading companion with proactive insights",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Accept",
            "Origin",
            "X-Requested-With",
        ],
    )

    # Register routes
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    # Health check
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": settings.project_name,
            "environment": settings.environment,
        }

    # Global exception handler
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger = structlog.get_logger(__name__)
        logger.error(
            "Unhandled exception",
            path=request.url.path,
            error=str(exc),
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": (
                    "An internal error occurred"
                    if not settings.debug
                    else str(exc)
                ),
                "code": "INTERNAL_ERROR",
            },
        )

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "apps.backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,  # Disable reload to fix port issue
    )
