# services/usage_service.py
"""
Usage tracking service implementation
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, UTC
import logging

from .interfaces.usage_interface import UsageServiceInterface
from .interfaces.cache_interface import CacheServiceInterface
from ..models.user import UsageRecord
from ..core.config import BaseSettings

logger = logging.getLogger(__name__)


class UsageService(UsageServiceInterface):
    """Implementation of usage tracking service"""

    def __init__(self, settings: BaseSettings, cache_service: CacheServiceInterface):
        self.settings = settings
        self.cache_service = cache_service
        self.usage_records = []  # In-memory storage for development

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
        try:
            usage_record = UsageRecord(
                user_id=user_id,
                endpoint=endpoint,
                request_type=request_type,
                timestamp=datetime.now(UTC),
                response_time_ms=response_time_ms,
                success=success,
                error_message=error_message,
                metadata=metadata or {},
            )

            # Store in memory for development
            # In production, this would go to a database
            self.usage_records.append(usage_record)

            # Also cache recent usage for quick access
            cache_key = f"usage:{user_id}:{usage_record.timestamp.strftime('%Y%m%d')}"
            cached_usage = await self.cache_service.get(cache_key) or []
            cached_usage.append(usage_record.dict())

            await self.cache_service.set(
                cache_key, cached_usage, expire=timedelta(days=2)
            )

            return True

        except Exception as e:
            logger.error(f"Error recording usage: {e}")
            return False

    async def get_user_usage(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[UsageRecord]:
        """Get usage records for a specific user"""
        try:
            # Filter records by user and date range
            filtered_records = [
                record for record in self.usage_records if record.user_id == user_id
            ]

            if start_date:
                filtered_records = [
                    record
                    for record in filtered_records
                    if record.timestamp >= start_date
                ]

            if end_date:
                filtered_records = [
                    record
                    for record in filtered_records
                    if record.timestamp <= end_date
                ]

            return filtered_records

        except Exception as e:
            logger.error(f"Error getting user usage: {e}")
            return []

    async def get_department_usage(
        self,
        department: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get aggregated usage for a department"""
        try:
            # This would require joining with user data in production
            # For development, return mock data

            total_requests = len(
                [
                    record
                    for record in self.usage_records
                    if start_date is None or record.timestamp >= start_date
                    if end_date is None or record.timestamp <= end_date
                ]
            )

            return {
                "department": department,
                "total_requests": total_requests,
                "unique_users": min(total_requests, 10),  # Mock data
                "success_rate": 0.95,
                "average_response_time_ms": 2500,
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                },
            }

        except Exception as e:
            logger.error(f"Error getting department usage: {e}")
            return {"error": str(e)}

    async def get_system_usage(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "day",
    ) -> Dict[str, Any]:
        """Get system-wide usage statistics"""
        try:
            # Filter records by date range
            filtered_records = self.usage_records

            if start_date:
                filtered_records = [
                    record
                    for record in filtered_records
                    if record.timestamp >= start_date
                ]

            if end_date:
                filtered_records = [
                    record
                    for record in filtered_records
                    if record.timestamp <= end_date
                ]

            total_requests = len(filtered_records)
            successful_requests = len([r for r in filtered_records if r.success])
            unique_users = len(set(record.user_id for record in filtered_records))

            response_times = [
                record.response_time_ms
                for record in filtered_records
                if record.response_time_ms is not None
            ]

            avg_response_time = (
                sum(response_times) / len(response_times) if response_times else 0
            )

            return {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "unique_users": unique_users,
                "success_rate": (
                    successful_requests / total_requests if total_requests > 0 else 0
                ),
                "average_response_time_ms": avg_response_time,
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "group_by": group_by,
                },
            }

        except Exception as e:
            logger.error(f"Error getting system usage: {e}")
            return {"error": str(e)}

    async def cleanup_old_records(self, days_to_keep: int = 365) -> int:
        """Clean up old usage records"""
        try:
            cutoff_date = datetime.now(UTC) - timedelta(days=days_to_keep)

            old_records_count = len(
                [
                    record
                    for record in self.usage_records
                    if record.timestamp < cutoff_date
                ]
            )

            # Remove old records
            self.usage_records = [
                record
                for record in self.usage_records
                if record.timestamp >= cutoff_date
            ]

            return old_records_count

        except Exception as e:
            logger.error(f"Error cleaning up old records: {e}")
            return 0
