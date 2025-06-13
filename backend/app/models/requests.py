# models/requests.py
"""
API request and response models
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class RecommendationRequest(BaseModel):
    """Request for course recommendations"""

    query: str = Field(..., min_length=10, max_length=1000)
    levels: Optional[List[int]] = Field(None, description="Course levels to include")
    max_results: int = Field(10, ge=1, le=50)
    include_explanations: bool = True
    user_preferences: Optional[Dict[str, Any]] = None


class RecommendationResponse(BaseModel):
    """Response with course recommendations"""

    recommendations: List[SimilarCourse]
    query: str
    total_courses_searched: int
    search_time_ms: int
    request_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Optional explanation
    search_explanation: Optional[str] = None
    generated_course_description: Optional[str] = None


class AuthRequest(BaseModel):
    """Authentication request"""

    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None  # For external auth
    auth_provider: Optional[str] = None


class AuthResponse(BaseModel):
    """Authentication response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User
    permissions: List[str] = Field(default_factory=list)


class UsageStatsRequest(BaseModel):
    """Request for usage statistics"""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[str] = None
    department: Optional[str] = None
    group_by: str = Field("day", regex="^(hour|day|week|month)$")


class UsageStatsResponse(BaseModel):
    """Usage statistics response"""

    total_requests: int
    unique_users: int
    average_response_time_ms: float
    success_rate: float
    usage_by_period: List[Dict[str, Any]]
    top_departments: List[Dict[str, Any]]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class HealthCheckResponse(BaseModel):
    """Health check response"""

    status: str = "healthy"
    version: str
    environment: str
    services: Dict[str, str]  # service_name -> status
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response"""

    error: str
    message: str
    code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Quota and Rate Limiting Models
class QuotaInfo(BaseModel):
    """User quota information"""

    user_id: str
    current_usage: int
    quota_limit: int
    reset_time: datetime
    quota_type: str  # daily, weekly, monthly


class RateLimitInfo(BaseModel):
    """Rate limit information"""

    requests_remaining: int
    reset_time: datetime
    retry_after_seconds: Optional[int] = None
