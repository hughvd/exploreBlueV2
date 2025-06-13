# api/v1/recommendations.py
"""
Recommendation API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import Optional, List
import logging

from ...core.dependencies import (
    get_recommendation_service,
    get_current_user_optional,
    check_rate_limit,
    check_quota,
    get_logging_context,
)
from ...models.user import User
from ...models.requests import RecommendationRequest, RecommendationResponse
from ...models.course import CourseFilter
from ...services.recommendation_service import RecommendationService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    current_user: Optional[User] = Depends(check_rate_limit),  # This also gets user
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    logging_context: dict = Depends(get_logging_context),
):
    """
    Get course recommendations based on user query

    - **query**: Description of what the user wants to learn
    - **levels**: Optional list of course levels to include (100, 200, 300, etc.)
    - **max_results**: Maximum number of recommendations to return (1-50)
    - **include_explanations**: Whether to include detailed explanations
    """
    try:
        logger.info(
            f"Recommendation request from user {current_user.id if current_user else 'anonymous'}: "
            f"{request.query[:100]}...",
            extra=logging_context,
        )

        # Check quota for authenticated users
        if current_user:
            # This will raise HTTPException if quota exceeded
            await check_quota(current_user)

        # Get recommendations
        response = await recommendation_service.get_recommendations(
            request=request, user=current_user
        )

        logger.info(
            f"Returned {len(response.recommendations)} recommendations "
            f"in {response.search_time_ms}ms",
            extra=logging_context,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_recommendations: {e}", extra=logging_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations",
        )


@router.post("/stream")
async def stream_recommendations(
    request: RecommendationRequest,
    current_user: Optional[User] = Depends(check_rate_limit),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
    logging_context: dict = Depends(get_logging_context),
):
    """
    Stream course recommendations as they are generated

    Returns a streaming response with real-time recommendation generation.
    """
    try:
        logger.info(
            f"Streaming recommendation request from user {current_user.id if current_user else 'anonymous'}",
            extra=logging_context,
        )

        # Check quota for authenticated users
        if current_user:
            await check_quota(current_user)

        async def generate_stream():
            try:
                async for chunk in recommendation_service.stream_recommendations(
                    request=request, user=current_user
                ):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Error in streaming: {e}", extra=logging_context)
                yield f"data: Error: {str(e)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-ID": logging_context.get("request_id", "unknown"),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in stream_recommendations: {e}", extra=logging_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stream recommendations",
        )


@router.get("/course/{course_id}")
async def get_course_details(
    course_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Get detailed information about a specific course"""
    try:
        course_details = await recommendation_service.get_course_details(course_id)

        if not course_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
            )

        return course_details

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting course details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get course details",
        )


@router.get("/course/{course_id}/similar")
async def get_similar_courses(
    course_id: str,
    limit: int = 10,
    current_user: Optional[User] = Depends(get_current_user_optional),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Get courses similar to a specific course"""
    try:
        if limit < 1 or limit > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 50",
            )

        similar_courses = await recommendation_service.get_similar_courses(
            course_id=course_id, limit=limit
        )

        return {
            "course_id": course_id,
            "similar_courses": [
                {
                    "course": course.course.dict(),
                    "similarity_score": course.similarity_score,
                    "relevance_explanation": course.relevance_explanation,
                }
                for course in similar_courses
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting similar courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get similar courses",
        )


@router.post("/explain")
async def explain_course_relevance(
    course_id: str,
    user_query: str,
    current_user: Optional[User] = Depends(get_current_user_optional),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Explain why a course is relevant to a user's interests"""
    try:
        explanation = await recommendation_service.explain_course_relevance(
            course_id=course_id, user_query=user_query
        )

        if not explanation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found or explanation could not be generated",
            )

        return {
            "course_id": course_id,
            "user_query": user_query,
            "explanation": explanation,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error explaining course relevance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate explanation",
        )


@router.get("/search")
async def search_courses(
    q: str,
    levels: Optional[List[int]] = None,
    departments: Optional[List[str]] = None,
    limit: int = 20,
    current_user: Optional[User] = Depends(get_current_user_optional),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Search courses by text query"""
    try:
        if not q or len(q.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query must be at least 3 characters long",
            )

        if limit < 1 or limit > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 100",
            )

        filters = CourseFilter(
            levels=levels, departments=departments, include_inactive=False
        )

        results = await recommendation_service.search_courses(
            query=q.strip(), filters=filters, limit=limit
        )

        return {
            "query": q,
            "filters": {"levels": levels, "departments": departments},
            "results": results,
            "total_results": len(results),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search courses",
        )


@router.get("/stats")
async def get_recommendation_stats(
    current_user: Optional[User] = Depends(get_current_user_optional),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
):
    """Get statistics about the recommendation system"""
    try:
        stats = await recommendation_service.get_recommendation_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting recommendation stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get recommendation statistics",
        )
