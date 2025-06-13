"""
Core configuration management for ExploreBlueV2
Supports multiple environments and university-specific settings
"""

from pydantic import BaseSettings, Field
from typing import Dict, List, Optional
from enum import Enum
from functools import lru_cache


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class AuthProvider(str, Enum):
    LOCAL = "local"
    SAML = "saml"
    OAUTH = "oauth"
    UNIVERSITY_SSO = "university_sso"


class BaseSettings(BaseSettings):
    """Base configuration settings"""

    # Application
    app_name: str = "ExploreBlue"
    app_version: str = "2.0.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    access_token_expire_minutes: int = 30

    # Database URLs
    redis_url: str = "redis://localhost:6379"
    postgres_url: Optional[str] = None

    # External Services
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_api_version: str = "2024-02-01"
    openai_api_base: str = Field(..., env="OPENAI_API_BASE")
    openai_organization_id: str = Field(..., env="OPENAI_ORGANIZATION_ID")

    # Models
    generator_model: str = "gpt-35-turbo"
    recommender_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-ada-002"

    # Rate Limiting
    rate_limit_requests: int = 1000
    rate_limit_period: int = 604800  # 1 week in seconds
    max_concurrent_requests: int = 10

    # Vector Database
    vector_db_url: str = "http://localhost:8080"
    vector_collection_name: str = "course_embeddings"

    # Caching
    cache_ttl_seconds: int = 3600  # 1 hour
    embedding_cache_size: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = False


class DevelopmentSettings(BaseSettings):
    """Development environment settings"""

    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True

    # Auth
    auth_provider: AuthProvider = AuthProvider.LOCAL
    require_authentication: bool = False

    # Relaxed limits for development
    rate_limit_requests: int = 10000
    max_concurrent_requests: int = 5

    # Local services
    redis_url: str = "redis://localhost:6379"
    vector_db_url: str = "http://localhost:8080"


class TestingSettings(BaseSettings):
    """Testing environment settings"""

    environment: Environment = Environment.TESTING
    debug: bool = True

    # Auth
    auth_provider: AuthProvider = AuthProvider.LOCAL
    require_authentication: bool = False

    # In-memory for testing
    redis_url: str = "redis://localhost:6380"
    vector_db_url: str = "memory://"

    # Fast testing
    cache_ttl_seconds: int = 1
    access_token_expire_minutes: int = 1


class UniversitySettings(BaseSettings):
    """University-specific configuration"""

    environment: Environment = Environment.PRODUCTION
    debug: bool = False

    # University Information
    university_name: str = Field(..., env="UNIVERSITY_NAME")
    university_domain: str = Field(..., env="UNIVERSITY_DOMAIN")
    university_id: str = Field(..., env="UNIVERSITY_ID")

    # Authentication
    auth_provider: AuthProvider = Field(..., env="AUTH_PROVIDER")
    require_authentication: bool = True

    # SAML Configuration
    saml_entity_id: Optional[str] = Field(None, env="SAML_ENTITY_ID")
    saml_sso_url: Optional[str] = Field(None, env="SAML_SSO_URL")
    saml_x509_cert: Optional[str] = Field(None, env="SAML_X509_CERT")

    # OAuth Configuration
    oauth_client_id: Optional[str] = Field(None, env="OAUTH_CLIENT_ID")
    oauth_client_secret: Optional[str] = Field(None, env="OAUTH_CLIENT_SECRET")
    oauth_provider_url: Optional[str] = Field(None, env="OAUTH_PROVIDER_URL")

    # Department-specific quotas
    department_quotas: Dict[str, int] = Field(
        default_factory=lambda: {
            "engineering": 1000,
            "liberal_arts": 500,
            "business": 300,
            "default": 100,
        }
    )

    # Role-based quotas
    role_quotas: Dict[str, int] = Field(
        default_factory=lambda: {
            "student": 50,
            "faculty": 200,
            "staff": 100,
            "admin": 1000,
        }
    )

    # Course level access by role
    course_level_access: Dict[str, List[int]] = Field(
        default_factory=lambda: {
            "student": [100, 200, 300, 400],
            "graduate_student": [100, 200, 300, 400, 500, 600, 700],
            "faculty": [100, 200, 300, 400, 500, 600, 700, 800, 900],
            "staff": [100, 200, 300, 400],
            "admin": [100, 200, 300, 400, 500, 600, 700, 800, 900],
        }
    )

    # Analytics and Monitoring
    enable_analytics: bool = True
    analytics_retention_days: int = 365

    # University-specific features
    enable_prerequisites_check: bool = False
    enable_grade_integration: bool = False
    enable_schedule_integration: bool = False


class UMichSettings(UniversitySettings):
    """University of Michigan specific settings"""

    university_name: str = "University of Michigan"
    university_domain: str = "umich.edu"
    university_id: str = "umich"

    # UM-specific auth
    auth_provider: AuthProvider = AuthProvider.SAML
    saml_entity_id: str = "https://shibboleth.umich.edu"

    # UM-specific quotas
    department_quotas: Dict[str, int] = Field(
        default_factory=lambda: {
            "engineering": 2000,
            "lsa": 1500,
            "business": 800,
            "medicine": 600,
            "education": 400,
            "default": 200,
        }
    )


@lru_cache()
def get_settings() -> BaseSettings:
    """
    Get settings based on environment variable
    Cached for performance
    """
    environment = Environment(os.getenv("ENVIRONMENT", "development"))
    university = os.getenv("UNIVERSITY_CONFIG", None)

    if environment == Environment.TESTING:
        return TestingSettings()
    elif environment == Environment.DEVELOPMENT:
        return DevelopmentSettings()
    elif university == "umich":
        return UMichSettings()
    elif environment in [Environment.STAGING, Environment.PRODUCTION]:
        return UniversitySettings()
    else:
        return DevelopmentSettings()


# Global settings instance
settings = get_settings()


# Configuration validation
def validate_configuration():
    """Validate that all required configuration is present"""
    errors = []

    if not settings.secret_key:
        errors.append("SECRET_KEY is required")

    if not settings.openai_api_key:
        errors.append("OPENAI_API_KEY is required")

    if settings.auth_provider == AuthProvider.SAML:
        if not getattr(settings, "saml_entity_id", None):
            errors.append("SAML_ENTITY_ID is required for SAML auth")

    if settings.auth_provider == AuthProvider.OAUTH:
        if not getattr(settings, "oauth_client_id", None):
            errors.append("OAUTH_CLIENT_ID is required for OAuth auth")

    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")

    return True


# Import os for environment variables
import os
