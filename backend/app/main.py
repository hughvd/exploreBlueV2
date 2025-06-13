"""
ExploreBlueV2 Main Application
FastAPI application with clean architecture and dependency injection
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from typing import Dict, Any

from app.core.config import get_settings, validate_configuration
from app.core.dependencies import cleanup_resources, get_service_health
from app.api.v1 import auth, recommendations, admin
from app.models.requests import ErrorResponse, HealthCheckResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    # Validate configuration
    try:
        validate_configuration()
        logger.info("Configuration validation passed")
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise

    # Initialize services (dependency injection will handle this)
    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application")
    await cleanup_resources()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="AI-powered course recommendation system with clean architecture",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring"""
    start_time = time.time()

    # Add request ID to headers if not present
    request_id = request.headers.get("X-Request-ID", "unknown")

    # Log request
    logger.info(
        f"Request {request_id}: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )

    try:
        response = await call_next(request)

        # Calculate response time
        process_time = time.time() - start_time

        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        # Log response
        logger.info(
            f"Response {request_id}: {response.status_code} " f"in {process_time:.3f}s"
        )

        return response

    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request {request_id} failed after {process_time:.3f}s: {str(e)}")

        # Return error response
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="Internal Server Error",
                message="An unexpected error occurred",
                request_id=request_id,
            ).dict(),
            headers={"X-Request-ID": request_id},
        )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    request_id = request.headers.get("X-Request-ID", "unknown")

    logger.error(
        f"Unhandled exception in request {request_id}: {str(exc)}", exc_info=True
    )

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            message="An unexpected error occurred" if not settings.debug else str(exc),
            request_id=request_id,
        ).dict(),
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name} v{settings.app_version}",
        "environment": settings.environment,
        "status": "healthy",
        "docs_url": "/docs" if settings.debug else "disabled",
    }


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    try:
        services_health = await get_service_health()

        # Determine overall status
        overall_status = "healthy"
        for service_status in services_health.values():
            if "unhealthy" in service_status.lower():
                overall_status = "degraded"
                break

        return HealthCheckResponse(
            status=overall_status,
            version=settings.app_version,
            environment=settings.environment.value,
            services=services_health,
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            version=settings.app_version,
            environment=settings.environment.value,
            services={"error": str(e)},
        )


# Include API routers
app.include_router(
    auth.router, prefix=settings.api_prefix + "/auth", tags=["Authentication"]
)

app.include_router(
    recommendations.router,
    prefix=settings.api_prefix + "/recommendations",
    tags=["Recommendations"],
)

app.include_router(
    admin.router, prefix=settings.api_prefix + "/admin", tags=["Administration"]
)


# Additional endpoints for development
if settings.debug:

    @app.get("/debug/config")
    async def debug_config():
        """Debug endpoint to view configuration (development only)"""
        return {
            "app_name": settings.app_name,
            "environment": settings.environment,
            "debug": settings.debug,
            "api_prefix": settings.api_prefix,
            "auth_provider": getattr(settings, "auth_provider", "not_set"),
            "require_authentication": getattr(settings, "require_authentication", True),
        }

    @app.get("/debug/services")
    async def debug_services():
        """Debug endpoint to check service status"""
        return await get_service_health()


# Development server entry point
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug",
    )
