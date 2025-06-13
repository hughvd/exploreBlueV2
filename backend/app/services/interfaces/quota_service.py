# services/interfaces/quota_service.py
"""
Quota and rate limiting service interface
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from ...models.user import User


class QuotaServiceInterface(ABC):
    """Abstract interface for quota and rate limiting"""

    @abstractmethod
    async def check_rate_limit(self, user: User) -> Dict[str, Any]:
        """Check if user is within rate limits"""
        pass

    @abstractmethod
    async def check_quota(self, user: User) -> Dict[str, Any]:
        """Check if user is within quota limits"""
        pass

    @abstractmethod
    async def record_request(self, user: User) -> bool:
        """Record a request for quota/rate limit tracking"""
        pass

    @abstractmethod
    async def get_quota_info(self, user: User) -> Dict[str, Any]:
        """Get current quota information for user"""
        pass

    @abstractmethod
    async def reset_user_quota(self, user_id: str) -> bool:
        """Reset quota for a specific user (admin function)"""
        pass

    @abstractmethod
    async def update_user_quota(self, user_id: str, new_quota: int) -> bool:
        """Update quota limit for a specific user"""
        pass
