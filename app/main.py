"""
Main application module for FastAPI Azure Backend.

This module initializes the FastAPI application with all routes, middleware,
and configuration settings.
"""

import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from api.auth.routes import router as auth_router
from api.files.routes import router as files_router
from api.tasks.routes import router as tasks_router
from api.tasks.summarization_routes import router as summarization_router
from api.tasks.translation_routes import router as translation_router
from api.chat.routes import router as chat_router
from api.admin.routes import router as admin_router
from api.admin.role_routes import router as role_router
from api.admin.task_routes import router as task_router

from integrations.azure_cosmos_db import initialize_cosmos_client, close_cosmos_client
from integrations.azure_blob import initialize_blob_client, close_blob_client
from integrations.azure_openai import initialize_openai_client
from integrations.azure_translator import initialize_translator_client
from utils.middleware import RequestLoggingMiddleware, JWTAuthMiddleware

# Configure logging
logging.basicConfig(
    level=logging.ERROR if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events for initializing and closing clients.
    """
    # Startup
    logger.info("Initializing application services and clients...")
    
    # Initialize Azure services
    await initialize_cosmos_client()
    await initialize_blob_client()
    await initialize_openai_client()
    await initialize_translator_client()
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Close Azure services
    await close_cosmos_client()
    await close_blob_client()
    
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_TITLE,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENABLE_DOCS else None,
    redoc_url="/redoc" if settings.ENABLE_DOCS else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(JWTAuthMiddleware, public_routes=["/", "/health", "/api/auth"])

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(files_router, prefix="/api/files", tags=["File Library"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat Sessions"])

app.include_router(summarization_router, prefix="/api/tasks", tags=["Tasks - Summarization"])
app.include_router(translation_router, prefix="/api/tasks", tags=["Tasks - Translation"])

app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(role_router, prefix="/api/admin", tags=["Admin - Roles"])
app.include_router(task_router, prefix="/api/admin", tags=["Admin - Tasks"])


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint for health check."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "cosmos_db": True,  # These would be actual checks in production
            "blob_storage": True,
            "openai": True,
            "translator": True,
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug",
    )



