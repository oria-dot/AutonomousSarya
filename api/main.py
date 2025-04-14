"""
Main API module for SARYA.
Provides FastAPI application configuration and routing.
"""
import logging
import os
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.endpoints import clone_api, metrics_api, plugin_api, reflex_api
from core.config import config_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api")

# Load configuration
config_manager.load()

# Create FastAPI application
app = FastAPI(
    title="SARYA API",
    description="API for SARYA - AI Intelligence Framework",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files if directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(clone_api.router, prefix="/api/v1")
app.include_router(plugin_api.router, prefix="/api/v1")
app.include_router(metrics_api.router, prefix="/api/v1")
app.include_router(reflex_api.router, prefix="/api/v1")

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint, returns basic API information."""
    return {
        "name": "SARYA API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc),
            "path": request.url.path,
            "timestamp": datetime.now().isoformat(),
        },
    )

def start_api():
    """Start the API server."""
    host = config_manager.get("api.host", "0.0.0.0")
    port = config_manager.get("api.port", 8000)
    workers = config_manager.get("api.workers", 1)
    
    logger.info(f"Starting API server on {host}:{port} with {workers} workers")
    
    # Use uvicorn to run the server
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
    )

if __name__ == "__main__":
    start_api()
