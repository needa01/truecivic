"""
FastAPI application for Parliament Explorer API.

Provides RESTful endpoints for bills, politicians, votes, and debates.

Responsibility: Main API application setup and configuration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Parliament Explorer API",
    description="RESTful API for Canadian parliamentary data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure specific origins for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "Parliament Explorer API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "bills": "/api/v1/ca/bills",
            "politicians": "/api/v1/ca/politicians",
            "votes": "/api/v1/ca/votes",
            "debates": "/api/v1/ca/debates",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "parliament-explorer-api"
    }


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


# Import and include routers
from api.v1.endpoints import bills, politicians, votes, debates

app.include_router(
    bills.router,
    prefix="/api/v1/ca",
    tags=["bills"]
)

app.include_router(
    politicians.router,
    prefix="/api/v1/ca",
    tags=["politicians"]
)

app.include_router(
    votes.router,
    prefix="/api/v1/ca",
    tags=["votes"]
)

app.include_router(
    debates.router,
    prefix="/api/v1/ca",
    tags=["debates"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
