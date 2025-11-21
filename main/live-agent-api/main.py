from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from infra import init_db, close_db, init_s3, close_s3, init_fish_audio, close_fish_audio
from api.v1 import api_router
from utils.exceptions import APIException


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    print("Starting up Live Agent API...")
    await init_db()
    print("Database initialized")
    await init_s3()
    print("S3 connection initialized")
    await init_fish_audio()
    print("Fish Audio client initialized")
    
    yield
    
    # Shutdown
    print("Shutting down Live Agent API...")
    await close_db()
    print("Database connections closed")
    await close_s3()
    print("S3 connections closed")
    await close_fish_audio()
    print("Fish Audio client closed")


# Create FastAPI application
app = FastAPI(
    title="Live Agent API",
    description="Live Agent API - Python FastAPI implementation",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """Handle custom API exceptions"""
    return JSONResponse(
        status_code=200,  # Always return 200, error code in response body
        content={
            "code": exc.code,
            "message": exc.message,
            "data": {}
        }
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "code": 200,
        "message": "success",
        "data": {
            "status": "healthy",
            "service": "live-agent-api",
            "version": "0.1.0"
        }
    }


# Include API router
app.include_router(api_router, prefix="/api/live_agent/v1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

