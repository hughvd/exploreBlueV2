# repositories/interfaces/usage_repository.py
"""
Usage tracking repository interface
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from ...models.user import UsageRecord


class UsageRepositoryInterface(ABC):
    """Abstract interface for usage tracking data operations"""

    @abstractmethod
    async def record_usage(self, usage_record: UsageRecord) -> bool:
        """Record a usage event"""
        pass

    @abstractmethod
    async def get_user_usage(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[UsageRecord]:
        """Get usage records for a specific user"""
        pass

    @abstractmethod
    async def get_user_usage_count(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Get count of usage records for a user"""
        pass

    @abstractmethod
    async def get_department_usage(
        self,
        department: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[UsageRecord]:
        """Get usage records for a department"""
        pass

    @abstractmethod
    async def get_department_usage_stats(
        self,
        department: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get aggregated usage statistics for a department"""
        pass

    @abstractmethod
    async def get_system_usage_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "day",
    ) -> Dict[str, Any]:
        """Get system-wide usage statistics"""
        pass

    @abstractmethod
    async def get_usage_by_endpoint(
        self,
        endpoint: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[UsageRecord]:
        """Get usage records for a specific endpoint"""
        pass

    @abstractmethod
    async def get_top_users(
        self,
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get top users by usage count"""
        pass

    @abstractmethod
    async def get_usage_trends(
        self,
        period: str = "day",  # day, week, month
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Get usage trends over time"""
        pass

    @abstractmethod
    async def cleanup_old_records(self, days_to_keep: int = 365) -> int:
        """Clean up old usage records"""
        pass

    @abstractmethod
    async def get_error_rates(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, float]:
        """Get error rates by endpoint"""
        pass

    @abstractmethod
    async def get_response_time_stats(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get response time statistics"""
        pass
