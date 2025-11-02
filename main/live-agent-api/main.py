"""
Live Agent Dashboard API

FastAPI application entry point for the Live Agent configuration API.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from orm import init_database, close_database
from utils.id_generator import init_id_generator, close_id_generator
from router import agent_router


# Configure logging
settings.configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events handler
    
    Handles startup and shutdown operations.
    """
    # Startup
    logger.info("Starting Live Agent Dashboard API...")
    
    # Initialize ID generator
    init_id_generator(instance_id=settings.instance_id)
    logger.info(f"Initialized ID generator (instance={settings.instance_id})")
    
    # Initialize database
    await init_database()
    
    logger.info(f"Application started in {settings.app_env} mode")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Live Agent Dashboard API...")
    await close_database()
    close_id_generator()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Live Agent Dashboard API",
    description=(
        "API service for managing voice assistant agents, devices, and bindings.\n\n"
        "This API provides comprehensive endpoints for:\n"
        "- Agent Management: Create, configure, and manage voice assistant agents\n"
        "- Device Management: Register and manage physical devices\n"
        "- Binding Management: Link agents to devices\n"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure proper origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(agent_router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "service": "Live Agent Dashboard API",
        "version": "0.1.0",
        "status": "running",
        "environment": settings.app_env,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.app_env,
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run with uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=settings.app_env == "development",
        log_level=settings.log_level.lower(),
    )
