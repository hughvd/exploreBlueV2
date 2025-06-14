# services/quota_service.py
"""
Quota and rate limiting service implementation
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

from .interfaces.quota_interface import QuotaServiceInterface
from .interfaces.cache_interface import CacheServiceInterface
from .interfaces.usage_interface import UsageServiceInterface
from ..models.user import User, UserRole
from ..core.config import BaseSettings

logger = logging.getLogger(__name__)


class QuotaService(QuotaServiceInterface):
    """Implementation of quota and rate limiting service"""
    
    def __init__(
        self, 
        settings: BaseSettings,
        cache_service: CacheServiceInterface,
        usage_service: UsageServiceInterface
    ):
        self.settings = settings
        self.cache_service = cache_service
        self.usage_service = usage_service
    
    async def check_rate_limit(self, user: User) -> Dict[str, Any]:
        """Check if user is within rate limits"""
        # Use a sliding window rate limit
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=60)  # 1 minute window
        
        # Rate limit key
        rate_limit_key = f"rate_limit:{user.id}:{now.strftime('%Y%m%d%H%M')}"
        
        # Get current request count in this minute
        current_count = await self.cache_service.get(rate_limit_key) or 0
        
        # Determine rate limit based on user role
        rate_limit = self._get_rate_limit_for_user(user)
        
        if current_count >= rate_limit:
            return {
                "allowed": False,
                "current_count": current_count,
                "limit": rate_limit,
                "reset_time": (now + timedelta(minutes=1)).isoformat(),
                "retry_after": 60
            }
        
        # Increment counter
        await self.cache_service.increment(rate_limit_key)
        await self.cache_service.set(
            rate_limit_key, 
            current_count + 1, 
            expire=timedelta(minutes=1)
        )
        
        return {
            "allowed": True,
            "current_count": current_count + 1,
            "limit": rate_limit,
            "reset_time": (now + timedelta(minutes=1)).isoformat()
        }
    
    async def check_quota(self, user: User) -> Dict[str, Any]:
        """Check if user is within quota limits"""
        # Daily quota check
        today = datetime.utcnow().date()
        
        # Get usage count for today
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        # For now, use cache to track daily usage
        # In production, this would query the usage service
        daily_usage_key = f"daily_usage:{user.id}:{today.isoformat()}"
        current_usage = await self.cache_service.get(daily_usage_key) or 0
        
        # Determine quota based on user role and department
        quota_limit = self._get_quota_for_user(user)
        
        if current_usage >= quota_limit:
            tomorrow = today + timedelta(days=1)
            reset_time = datetime.combine(tomorrow, datetime.min.time())
            
            return {
                "allowed": False,
                "current_usage": current_usage,
                "limit": quota_limit,
                "reset_time": reset_time.isoformat()
            }
        
        return {
            "allowed": True,
            "current_usage": current_usage,
            "limit": quota_limit,
            "reset_time": datetime.combine(
                today + timedelta(days=1), 
                datetime.min.time()
            ).isoformat()
        }
    
    async def record_request(self, user: User) -> bool:
        """Record a request for quota/rate limit tracking"""
        try:
            today = datetime.utcnow().date()
            
            # Increment daily usage counter
            daily_usage_key = f"daily_usage:{user.id}:{today.isoformat()}"
            await self.cache_service.increment(daily_usage_key)
            
            # Set expiry to end of tomorrow (to handle timezone issues)
            tomorrow_end = datetime.combine(
                today + timedelta(days=2), 
                datetime.min.time()
            )
            expire_delta = tomorrow_end - datetime.utcnow()
            
            # Refresh the expiry time
            current_count = await self.cache_service.get(daily_usage_key) or 1
            await self.cache_service.set(
                daily_usage_key, 
                current_count, 
                expire=expire_delta
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error recording request for user {user.id}: {e}")
            return False
    
    async def get_quota_info(self, user: User) -> Dict[str, Any]:
        """Get current quota information for user"""
        today = datetime.utcnow().date()
        daily_usage_key = f"daily_usage:{user.id}:{today.isoformat()}"
        current_usage = await self.cache_service.get(daily_usage_key) or 0
        
        quota_limit = self._get_quota_for_user(user)
        
        tomorrow = today + timedelta(days=1)
        reset_time = datetime.combine(tomorrow, datetime.min.time())
        
        return {
            "user_id": user.id,
            "current_usage": current_usage,
            "quota_limit": quota_limit,
            "remaining": max(0, quota_limit - current_usage),
            "reset_time": reset_time.isoformat(),
            "quota_type": "daily"
        }
    
    async def reset_user_quota(self, user_id: str) -> bool:
        """Reset quota for a specific user (admin function)"""
        try:
            today = datetime.utcnow().date()
            daily_usage_key = f"daily_usage:{user_id}:{today.isoformat()}"
            
            return await self.cache_service.delete(daily_usage_key)
            
        except Exception as e:
            logger.error(f"Error resetting quota for user {user_id}: {e}")
            return False
    
    async def update_user_quota(self, user_id: str, new_quota: int) -> bool:
        """Update quota limit for a specific user"""
        # In a production system, this would update user-specific quota overrides
        # For now, we'll store it in cache
        try:
            quota_override_key = f"quota_override:{user_id}"
            await self.cache_service.set(
                quota_override_key, 
                new_quota,
                expire=timedelta(days=30)  # Override expires in 30 days
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating quota for user {user_id}: {e}")
            return False
    
    def _get_rate_limit_for_user(self, user: User) -> int:
        """Get rate limit (requests per minute) for user"""
        # Base rate limits by role
        base_limits = {
            UserRole.GUEST: 5,
            UserRole.STUDENT: 20,
            UserRole.GRADUATE_STUDENT: 30,
            UserRole.FACULTY: 50,
            UserRole.STAFF: 40,
            UserRole.ADMIN: 100
        }
        
        return base_limits.get(user.role, 10)
    
    def _get_quota_for_user(self, user: User) -> int:
        """Get daily quota for user based on role and department"""
        # Check for user-specific quota override
        quota_override_key = f"quota_override:{user.id}"
        # Note: In real implementation, this would be async
        # For now, assume no override
        
        # Base quotas by role
        role_quotas = getattr(self.settings, 'role_quotas', {
            UserRole.GUEST.value: 10,
            UserRole.STUDENT.value: 50,
            UserRole.GRADUATE_STUDENT.value: 75,
            UserRole.FACULTY.value: 200,
            UserRole.STAFF.value: 100,
            UserRole.ADMIN.value: 1000
        })
        
        base_quota = role_quotas.get(user.role.value, 50)
        
        # Department-specific multipliers
        department_quotas = getattr(self.settings, 'department_quotas', {})
        if user.department and user.department in department_quotas:
            return department_quotas[user.department]
        
        return base_quota
