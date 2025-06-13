# api/v1/admin.py
"""
Administration API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from ...core.dependencies import (
    require_admin,
    require_faculty,
    get_usage_service,
    get_quota_service,
    get_recommendation_service,
    get_logging_context,
)
from ...models.user import User, UserRole
from ...models.requests import UsageStatsRequest, UsageStatsResponse
from ...services.interfaces.usage_interface import UsageServiceInterface
from ...services.interfaces.quota_interface import QuotaServiceInterface
from ...services.recommendation_service import RecommendationService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/usage/system")
async def get_system_usage(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    group_by: str = Query("day", regex="^(hour|day|week|month)$"),
    current_user: User = Depends(require_admin),
    usage_service: UsageServiceInterface = Depends(get_usage_service),
    logging_context: dict = Depends(get_logging_context),
):
    """Get system-wide usage statistics (Admin only)"""
    try:
        logger.info(
            f"System usage request by admin: {current_user.username}",
            extra=logging_context,
        )

        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        usage_stats = await usage_service.get_system_usage(
            start_date=start_date, end_date=end_date, group_by=group_by
        )

        return usage_stats

    except Exception as e:
        logger.error(f"Error getting system usage: {e}", extra=logging_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system usage statistics",
        )


@router.get("/usage/department/{department}")
async def get_department_usage(
    department: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_faculty),
    usage_service: UsageServiceInterface = Depends(get_usage_service),
    logging_context: dict = Depends(get_logging_context),
):
    """Get department usage statistics (Faculty/Admin only)"""
    try:
        # Faculty can only view their own department
        if (
            current_user.role == UserRole.FACULTY
            and current_user.department != department
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only view usage for your own department",
            )

        logger.info(
            f"Department usage request for {department} by: {current_user.username}",
            extra=logging_context,
        )

        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        usage_stats = await usage_service.get_department_usage(
            department=department, start_date=start_date, end_date=end_date
        )

        return usage_stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting department usage: {e}", extra=logging_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get department usage statistics",
        )


@router.get("/usage/user/{user_id}")
async def get_user_usage(
    user_id: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_admin),
    usage_service: UsageServiceInterface = Depends(get_usage_service),
    logging_context: dict = Depends(get_logging_context),
):
    """Get user usage statistics (Admin only)"""
    try:
        logger.info(
            f"User usage request for {user_id} by admin: {current_user.username}",
            extra=logging_context,
        )

        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)

        usage_records = await usage_service.get_user_usage(
            user_id=user_id, start_date=start_date, end_date=end_date
        )

        return {
            "user_id": user_id,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "total_requests": len(usage_records),
            "usage_records": [record.dict() for record in usage_records],
        }

    except Exception as e:
        logger.error(f"Error getting user usage: {e}", extra=logging_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user usage statistics",
        )


@router.post("/quota/reset/{user_id}")
async def reset_user_quota(
    user_id: str,
    current_user: User = Depends(require_admin),
    quota_service: QuotaServiceInterface = Depends(get_quota_service),
    logging_context: dict = Depends(get_logging_context),
):
    """Reset quota for a specific user (Admin only)"""
    try:
        logger.info(
            f"Quota reset for {user_id} by admin: {current_user.username}",
            extra=logging_context,
        )

        success = await quota_service.reset_user_quota(user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or quota reset failed",
            )

        return {
            "message": f"Quota reset successful for user {user_id}",
            "reset_by": current_user.username,
            "reset_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting quota: {e}", extra=logging_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reset user quota",
        )


@router.put("/quota/{user_id}")
async def update_user_quota(
    user_id: str,
    new_quota: int = Query(..., ge=1, le=10000),
    current_user: User = Depends(require_admin),
    quota_service: QuotaServiceInterface = Depends(get_quota_service),
    logging_context: dict = Depends(get_logging_context),
):
    """Update quota limit for a specific user (Admin only)"""
    try:
        logger.info(
            f"Quota update for {user_id} to {new_quota} by admin: {current_user.username}",
            extra=logging_context,
        )

        success = await quota_service.update_user_quota(user_id, new_quota)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found or quota update failed",
            )

        return {
            "message": f"Quota updated successfully for user {user_id}",
            "new_quota": new_quota,
            "updated_by": current_user.username,
            "updated_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating quota: {e}", extra=logging_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user quota",
        )


@router.get("/system/stats")
async def get_system_stats(
    current_user: User = Depends(require_admin),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    usage_service: UsageServiceInterface = Depends(get_usage_service),
):
    """Get comprehensive system statistics (Admin only)"""
    try:
        # Get recommendation system stats
        rec_stats = await recommendation_service.get_recommendation_stats()

        # Get system usage stats for last 7 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        usage_stats = await usage_service.get_system_usage(
            start_date=start_date, end_date=end_date
        )

        return {
            "recommendation_system": rec_stats,
            "usage_stats_7d": usage_stats,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system statistics",
        )


@router.post("/cleanup/usage")
async def cleanup_old_usage_records(
    days_to_keep: int = Query(365, ge=30, le=3650),
    current_user: User = Depends(require_admin),
    usage_service: UsageServiceInterface = Depends(get_usage_service),
    logging_context: dict = Depends(get_logging_context),
):
    """Clean up old usage records (Admin only)"""
    try:
        logger.info(
            f"Usage cleanup initiated by admin: {current_user.username}, keeping {days_to_keep} days",
            extra=logging_context,
        )

        deleted_count = await usage_service.cleanup_old_records(days_to_keep)

        return {
            "message": "Usage cleanup completed",
            "records_deleted": deleted_count,
            "days_kept": days_to_keep,
            "cleaned_by": current_user.username,
            "cleaned_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error cleaning up usage records: {e}", extra=logging_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup usage records",
        )
