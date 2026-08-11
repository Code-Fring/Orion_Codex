"""Main FastAPI application for Orion Codex."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import auth, projects, providers, tasks, websocket
from backend.config.settings import settings
from backend.core.providers.factory import ProviderFactory
from backend.core.providers.registry import provider_registry
from backend.database.connection import db_manager
from backend.tasks.queue import task_scheduler

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Orion Codex", version=settings.APP_VERSION)

    # Initialize database
    db_manager.initialize()
    await db_manager.create_all()
    logger.info("Database initialized")

    # Initialize AI providers from environment
    await initialize_providers()

    # Start task scheduler
    await task_scheduler.start()
    logger.info("Task scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down Orion Codex")
    await task_scheduler.stop()
    await provider_registry.close_all()
    await db_manager.close()
    logger.info("Shutdown complete")


async def initialize_providers() -> None:
    """Initialize AI providers from environment configuration."""
    from backend.config.settings import settings

    provider_configs = {
        "openai": {
            "api_key": settings.OPENAI_API_KEY,
            "base_url": "https://api.openai.com/v1",
        },
        "anthropic": {
            "api_key": settings.ANTHROPIC_API_KEY,
            "base_url": "https://api.anthropic.com",
        },
        "google": {
            "api_key": settings.GOOGLE_API_KEY,
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
        },
        "nvidia": {
            "api_key": settings.NVIDIA_API_KEY,
            "base_url": "https://integrate.api.nvidia.com/v1",
        },
        "deepseek": {
            "api_key": settings.DEEPSEEK_API_KEY,
            "base_url": "https://api.deepseek.com/v1",
        },
        "groq": {
            "api_key": settings.GROQ_API_KEY,
            "base_url": "https://api.groq.com/openai/v1",
        },
        "openrouter": {
            "api_key": settings.OPENROUTER_API_KEY,
            "base_url": "https://openrouter.ai/api/v1",
        },
        "omniroute": {
            "api_key": settings.OMNIROUTE_API_KEY,
            "base_url": "https://api.omniroute.ai/v1",
        },
        "claude_cli": {
            "cli_path": "claude",
            "working_dir": settings.WORKSPACE_ROOT,
        },
    }

    for provider_type, config in provider_configs.items():
        # Filter out None values
        filtered_config = {k: v for k, v in config.items() if v is not None}
        # For claude_cli, we don't need api_key
        if provider_type == "claude_cli" or filtered_config.get("api_key"):
            try:
                await ProviderFactory.create_provider(provider_type, filtered_config)
                logger.info(f"Initialized provider: {provider_type}")
            except Exception as e:
                logger.warning(f"Failed to initialize provider {provider_type}: {e}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Autonomous Software Engineering Platform",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception", path=request.url.path, error=str(exc), exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Health check
@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Include routers
app.include_router(projects.router, prefix=settings.API_PREFIX)
app.include_router(providers.router, prefix=settings.API_PREFIX)
app.include_router(tasks.router, prefix=settings.API_PREFIX)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(websocket.router, prefix=settings.API_PREFIX)


# Root endpoint
@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Autonomous Software Engineering Platform",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
