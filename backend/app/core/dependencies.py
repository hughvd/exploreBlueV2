"""
Dependency injection setup for ExploreBlueV2
Manages service lifecycle and provides clean dependency injection
"""

from functools import lru_cache
from typing import AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis.asyncio as redis
import logging

from .config import get_settings, BaseSettings
from ..models.user import User, UserRole
from ..services.interfaces import (
    AuthServiceInterface,
    VectorServiceInterface,
    LLMServiceInterface,
    UsageServiceInterface,
    CacheServiceInterface,
    QuotaServiceInterface,
)

# Import concrete implementations (we'll create these next)
from ..services.auth_service import AuthService
from ..services.vector_service import VectorService
from ..services.llm_service import LLMService
from ..services.usage_service import UsageService
from ..services.cache_service import RedisCacheService
from ..services.quota_service import QuotaService

# Import repositories
from ..repositories.interfaces import UserRepositoryInterface, CourseRepositoryInterface
from ..repositories.memory_user_repository import MemoryUserRepository
from ..repositories.memory_course_repository import MemoryCourseRepository

logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)


# Database Dependencies
@lru_cache()
def get_redis_pool():
    """Get Redis connection pool"""
    settings = get_settings()
    if settings.redis_url.startswith("redis://"):
        return redis.from_url(settings.redis_url)
    else:
        # For testing or memory-based scenarios
        return None


# Repository Dependencies
@lru_cache()
def get_user_repository() -> UserRepositoryInterface:
    """Get user repository instance"""
    # In production, this could be a database repository
    return MemoryUserRepository()


@lru_cache()
def get_course_repository() -> CourseRepositoryInterface:
    """Get course repository instance"""
    # In production, this could be a database repository
    return MemoryCourseRepository()


# Service Dependencies
@lru_cache()
def get_cache_service() -> CacheServiceInterface:
    """Get cache service instance"""
    redis_pool = get_redis_pool()
    settings = get_settings()
    return RedisCacheService(redis_pool, settings)


@lru_cache()
def get_vector_service() -> VectorServiceInterface:
    """Get vector service instance"""
    settings = get_settings()
    cache_service = get_cache_service()
    return VectorService(settings, cache_service)


@lru_cache()
def get_llm_service() -> LLMServiceInterface:
    """Get LLM service instance"""
    settings = get_settings()
    cache_service = get_cache_service()
    return LLMService(settings, cache_service)


@lru_cache()
def get_usage_service() -> UsageServiceInterface:
    """Get usage tracking service instance"""
    settings = get_settings()
    cache_service = get_cache_service()
    return UsageService(settings, cache_service)


@lru_cache()
def get_quota_service() -> QuotaServiceInterface:
    """Get quota service instance"""
    settings = get_settings()
    cache_service = get_cache_service()
    usage_service = get_usage_service()
    return QuotaService(settings, cache_service, usage_service)


@lru_cache()
def get_auth_service() -> AuthServiceInterface:
    """Get authentication service instance"""
    settings = get_settings()
    user_repository = get_user_repository()
    cache_service = get_cache_service()
    return AuthService(settings, user_repository, cache_service)


# Authentication Dependencies
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthServiceInterface = Depends(get_auth_service),
) -> Optional[User]:
    """Get current user from token (optional - returns None if not authenticated)"""
    if not credentials:
        return None

    try:
        user = await auth_service.authenticate_user(
            credentials.credentials,
            auth_provider=None,  # Will be determined by auth service
        )
        return user
    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthServiceInterface = Depends(get_auth_service),
) -> User:
    """Get current user from token (required - raises exception if not authenticated)"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await auth_service.authenticate_user(
            credentials.credentials, auth_provider=None
        )
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Role-based Dependencies
def require_role(required_role: UserRole):
    """Create a dependency that requires a specific role"""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}",
            )
        return current_user

    return role_checker


def require_any_role(*required_roles: UserRole):
    """Create a dependency that requires any of the specified roles"""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(required_roles)}",
            )
        return current_user

    return role_checker


# Specific role dependencies
require_admin = require_role(UserRole.ADMIN)
require_faculty = require_any_role(UserRole.FACULTY, UserRole.ADMIN)
require_student_or_faculty = require_any_role(
    UserRole.STUDENT, UserRole.GRADUATE_STUDENT, UserRole.FACULTY, UserRole.ADMIN
)


# Rate Limiting Dependencies
async def check_rate_limit(
    current_user: Optional[User] = Depends(get_current_user_optional),
    quota_service: QuotaServiceInterface = Depends(get_quota_service),
):
    """Check rate limits for the current request"""
    # For unauthenticated users, use IP-based rate limiting
    if not current_user:
        # Create a guest user for rate limiting purposes
        # In a real implementation, you'd get the IP address
        guest_user = User(
            id="guest",
            username="guest",
            email="guest@example.com",
            role=UserRole.GUEST,
            auth_provider="local",
        )
        current_user = guest_user

    rate_limit_result = await quota_service.check_rate_limit(current_user)
    if not rate_limit_result.get("allowed", True):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(rate_limit_result.get("retry_after", 60)),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(rate_limit_result.get("reset_time", "")),
            },
        )

    return current_user


async def check_quota(
    current_user: User = Depends(get_current_user),
    quota_service: QuotaServiceInterface = Depends(get_quota_service),
):
    """Check quota limits for the current user"""
    quota_result = await quota_service.check_quota(current_user)
    if not quota_result.get("allowed", True):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Quota exceeded. Limit: {quota_result.get('limit', 'unknown')}",
            headers={
                "X-Quota-Remaining": "0",
                "X-Quota-Reset": str(quota_result.get("reset_time", "")),
            },
        )

    return current_user


# Business Logic Dependencies
async def get_recommendation_service(
    vector_service: VectorServiceInterface = Depends(get_vector_service),
    llm_service: LLMServiceInterface = Depends(get_llm_service),
    course_repository: CourseRepositoryInterface = Depends(get_course_repository),
    usage_service: UsageServiceInterface = Depends(get_usage_service),
):
    """Get the recommendation service with all its dependencies"""
    from ..services.recommendation_service import RecommendationService

    return RecommendationService(
        vector_service=vector_service,
        llm_service=llm_service,
        course_repository=course_repository,
        usage_service=usage_service,
    )


# Health Check Dependencies
async def get_service_health() -> dict:
    """Get health status of all services"""
    health_status = {
        "database": "unknown",
        "redis": "unknown",
        "vector_db": "unknown",
        "llm_service": "unknown",
    }

    try:
        # Check Redis
        redis_pool = get_redis_pool()
        if redis_pool:
            await redis_pool.ping()
            health_status["redis"] = "healthy"
        else:
            health_status["redis"] = "disabled"
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"

    try:
        # Check Vector Service
        vector_service = get_vector_service()
        stats = await vector_service.get_collection_stats()
        health_status["vector_db"] = "healthy"
    except Exception as e:
        health_status["vector_db"] = f"unhealthy: {str(e)}"

    try:
        # Check LLM Service
        llm_service = get_llm_service()
        # Simple test call
        test_embedding = await llm_service.generate_embedding("test")
        if test_embedding:
            health_status["llm_service"] = "healthy"
    except Exception as e:
        health_status["llm_service"] = f"unhealthy: {str(e)}"

    return health_status


# Cleanup function for application shutdown
async def cleanup_resources():
    """Cleanup resources on application shutdown"""
    try:
        redis_pool = get_redis_pool()
        if redis_pool:
            await redis_pool.close()
    except Exception as e:
        logger.error(f"Error cleaning up Redis: {e}")

    # Clear caches
    get_redis_pool.cache_clear()
    get_user_repository.cache_clear()
    get_course_repository.cache_clear()
    get_cache_service.cache_clear()
    get_vector_service.cache_clear()
    get_llm_service.cache_clear()
    get_usage_service.cache_clear()
    get_quota_service.cache_clear()
    get_auth_service.cache_clear()


# Settings dependency
def get_app_settings() -> BaseSettings:
    """Get application settings"""
    return get_settings()


# Request ID dependency for tracking
from uuid import uuid4
from fastapi import Request


async def get_request_id(request: Request) -> str:
    """Generate or get request ID for tracking"""
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid4())
    return request_id


# Logging context dependency
async def get_logging_context(
    request_id: str = Depends(get_request_id),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """Get logging context for request tracking"""
    context = {
        "request_id": request_id,
        "user_id": current_user.id if current_user else "anonymous",
        "user_role": current_user.role if current_user else "guest",
    }
    return context
