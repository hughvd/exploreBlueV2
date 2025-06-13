# services/interfaces/usage_service.py
"""
Usage tracking service interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from ...models.user import UsageRecord


class UsageServiceInterface(ABC):
    """Abstract interface for usage tracking"""

    @abstractmethod
    async def record_request(
        self,
        user_id: str,
        endpoint: str,
        request_type: str,
        response_time_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Record a user request"""
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
    async def get_department_usage(
        self,
        department: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get aggregated usage for a department"""
        pass

    @abstractmethod
    async def get_system_usage(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "day",
    ) -> Dict[str, Any]:
        """Get system-wide usage statistics"""
        pass

    @abstractmethod
    async def cleanup_old_records(self, days_to_keep: int = 365) -> int:
        """Clean up old usage records"""
        pass
