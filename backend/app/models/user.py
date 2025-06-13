# models/user.py
"""
User-related data models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    STUDENT = "student"
    GRADUATE_STUDENT = "graduate_student"
    FACULTY = "faculty"
    STAFF = "staff"
    ADMIN = "admin"
    GUEST = "guest"


class AuthProvider(str, Enum):
    LOCAL = "local"
    SAML = "saml"
    OAUTH = "oauth"
    UNIVERSITY_SSO = "university_sso"


class User(BaseModel):
    """Core user model"""

    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    role: UserRole
    department: Optional[str] = None
    university_id: Optional[str] = None

    # Authentication metadata
    auth_provider: AuthProvider
    external_id: Optional[str] = None  # ID from external auth system

    # Preferences
    preferred_course_levels: List[int] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)

    # Status
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserPreferences(BaseModel):
    """User preferences for recommendations"""

    preferred_levels: List[int] = Field(default_factory=list)
    excluded_levels: List[int] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)
    max_recommendations: int = 10
    include_prerequisites: bool = False


class UserSession(BaseModel):
    """User session information"""

    user_id: str
    session_id: str
    auth_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None


class UsageRecord(BaseModel):
    """Track user API usage"""

    user_id: str
    endpoint: str
    request_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    response_time_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
