"""
FastAPI application for Parliament Explorer API.

Provides RESTful endpoints for bills, politicians, votes, and debates.

Responsibility: Main API application setup and configuration
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from src.config import settings
from api.middleware import RateLimiterMiddleware
from api.middleware.api_key_auth import APIKeyMiddleware
from src.db.session import get_db

# GraphQL imports (only if strawberry is installed)
try:
    from strawberry.fastapi import GraphQLRouter
    from api.graphql import schema
    GRAPHQL_AVAILABLE = True
except ImportError:
    GRAPHQL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Strawberry GraphQL not installed. GraphQL endpoint will not be available.")

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

# Configure CORS - Environment-specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,  # From config: dev=localhost, prod=specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-API-Key"],  # Allow X-API-Key header
)

# Configure API key authentication middleware
app.add_middleware(
    APIKeyMiddleware,
    protected_paths=["/api/v1/"]
)

# Configure rate limiting
rate_limiter = RateLimiterMiddleware(
    app,
    redis_url=settings.redis_url if hasattr(settings, 'redis_url') else None
)
app.add_middleware(RateLimiterMiddleware, redis_url=settings.redis_url if hasattr(settings, 'redis_url') else None)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Parliament Explorer API...")
    # Initialize rate limiter
    if hasattr(app, 'user_middleware'):
        for middleware in app.user_middleware:
            if isinstance(middleware.cls, type) and issubclass(middleware.cls, RateLimiterMiddleware):
                # Find the rate limiter instance
                pass
    logger.info("Rate limiter initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Parliament Explorer API...")


@app.get("/")
async def root():
    """Root endpoint - API information."""
    endpoints_dict = {
        "bills": "/api/v1/ca/bills",
        "politicians": "/api/v1/ca/politicians",
        "votes": "/api/v1/ca/votes",
        "debates": "/api/v1/ca/debates",
        "committees": "/api/v1/ca/committees",
        "feeds": "/api/v1/ca/feeds",
        "search": "/api/v1/ca/search",
        "graph": "/api/v1/ca/graph",
        "preferences": "/api/v1/ca/preferences",
        "docs": "/docs"
    }
    
    if GRAPHQL_AVAILABLE:
        endpoints_dict["graphql"] = "/graphql"
    
    return {
        "name": "Parliament Explorer API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": endpoints_dict
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
from api.v1.endpoints import bills, politicians, votes, debates, committees, feeds, search, graph, preferences, auth

app.include_router(
    auth.router,
    prefix="/api/v1",
    tags=["authentication"]
)

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

app.include_router(
    committees.router,
    prefix="/api/v1/ca",
    tags=["committees"]
)

app.include_router(
    feeds.router,
    prefix="/api/v1/ca",
    tags=["feeds"]
)

app.include_router(
    search.router,
    prefix="/api/v1/ca",
    tags=["search"]
)

app.include_router(
    graph.router,
    prefix="/api/v1/ca",
    tags=["graph"]
)

app.include_router(
    preferences.router,
    prefix="/api/v1/ca",
    tags=["preferences"]
)

# Mount GraphQL endpoint (if available)
if GRAPHQL_AVAILABLE:
    
    async def get_context(request: Request):
        """Context for GraphQL requests"""
        db = await anext(get_db())
        return {"request": request, "db": db}
    
    graphql_app = GraphQLRouter(
        schema,
        context_getter=get_context,
        graphiql=settings.app.debug  # Only enable GraphiQL in debug mode
    )
    app.include_router(graphql_app, prefix="/graphql")
    logger.info("GraphQL endpoint mounted at /graphql")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
