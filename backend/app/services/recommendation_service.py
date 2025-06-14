# services/recommendation_service.py
"""
Core recommendation service - orchestrates the recommendation process
"""
import time
from typing import List, Optional, AsyncGenerator
from uuid import uuid4
from datetime import datetime
import logging

from .interfaces.vector_interface import VectorServiceInterface
from .interfaces.llm_interface import LLMServiceInterface
from .interfaces.usage_interface import UsageServiceInterface
from ..repositories.interfaces.course_repository import CourseRepositoryInterface
from ..models.user import User
from ..models.course import CourseFilter, SimilarCourse
from ..models.requests import RecommendationRequest, RecommendationResponse

logger = logging.getLogger(__name__)


class RecommendationService:
    """Core service that orchestrates the recommendation process"""

    def __init__(
        self,
        vector_service: VectorServiceInterface,
        llm_service: LLMServiceInterface,
        course_repository: CourseRepositoryInterface,
        usage_service: UsageServiceInterface,
    ):
        self.vector_service = vector_service
        self.llm_service = llm_service
        self.course_repository = course_repository
        self.usage_service = usage_service

    async def get_recommendations(
        self, request: RecommendationRequest, user: Optional[User] = None
    ) -> RecommendationResponse:
        """Get course recommendations based on user query"""
        start_time = time.time()
        request_id = str(uuid4())

        try:
            logger.info(
                f"Starting recommendation request {request_id} for query: {request.query[:100]}..."
            )

            # Step 1: Generate ideal course description
            step_start = time.time()
            ideal_description = await self.llm_service.generate_course_description(
                request.query
            )
            logger.info(
                f"Generated course description in {time.time() - step_start:.2f}s"
            )

            # Step 2: Generate embedding for the ideal description
            step_start = time.time()
            query_embedding = await self.vector_service.generate_embedding(
                ideal_description
            )
            logger.info(f"Generated embedding in {time.time() - step_start:.2f}s")

            # Step 3: Create course filter based on request
            course_filter = CourseFilter(levels=request.levels, include_inactive=False)

            # Step 4: Find similar courses using vector search
            step_start = time.time()
            similar_courses = await self.vector_service.search_similar_courses(
                query_embedding=query_embedding,
                filters=course_filter,
                limit=min(
                    50, request.max_results * 3
                ),  # Get more candidates than needed
            )
            logger.info(
                f"Found {len(similar_courses)} similar courses in {time.time() - step_start:.2f}s"
            )

            if not similar_courses:
                logger.warning(f"No similar courses found for request {request_id}")
                return RecommendationResponse(
                    recommendations=[],
                    query=request.query,
                    total_courses_searched=0,
                    search_time_ms=int((time.time() - start_time) * 1000),
                    request_id=request_id,
                    search_explanation="No courses found matching your query and level preferences.",
                )

            # Step 5: Generate detailed recommendations using LLM
            step_start = time.time()

            # Prepare course data for LLM
            course_data = []
            for similar_course in similar_courses[
                : request.max_results * 2
            ]:  # Limit to avoid token limits
                course_dict = {
                    "course_code": similar_course.course.course_code,
                    "title": similar_course.course.title,
                    "description": similar_course.course.description,
                    "level": similar_course.course.level,
                    "department": similar_course.course.department,
                    "similarity_score": similar_course.similarity_score,
                }
                course_data.append(course_dict)

            # Generate recommendation text
            recommendation_text = await self.llm_service.generate_recommendations_text(
                query=request.query, similar_courses=course_data
            )
            logger.info(f"Generated recommendations in {time.time() - step_start:.2f}s")

            # Step 6: Add explanations if requested
            if request.include_explanations:
                for similar_course in similar_courses[: request.max_results]:
                    if not similar_course.relevance_explanation:
                        explanation = await self.llm_service.explain_recommendation(
                            course={
                                "course_code": similar_course.course.course_code,
                                "title": similar_course.course.title,
                                "description": similar_course.course.description,
                            },
                            user_query=request.query,
                        )
                        similar_course.relevance_explanation = explanation

            # Step 7: Record usage
            if user:
                await self.usage_service.record_request(
                    user_id=user.id,
                    endpoint="recommendations",
                    request_type="course_recommendation",
                    response_time_ms=int((time.time() - start_time) * 1000),
                    success=True,
                    metadata={
                        "query_length": len(request.query),
                        "results_returned": len(similar_courses[: request.max_results]),
                        "levels_requested": request.levels,
                        "request_id": request_id,
                    },
                )

            total_time_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"Completed recommendation request {request_id} in {total_time_ms}ms"
            )

            return RecommendationResponse(
                recommendations=similar_courses[: request.max_results],
                query=request.query,
                total_courses_searched=len(similar_courses),
                search_time_ms=total_time_ms,
                request_id=request_id,
                search_explanation=f"Found {len(similar_courses)} relevant courses based on your interests.",
                generated_course_description=ideal_description,
            )

        except Exception as e:
            logger.error(
                f"Error in recommendation request {request_id}: {e}", exc_info=True
            )

            # Record error usage
            if user:
                await self.usage_service.record_request(
                    user_id=user.id,
                    endpoint="recommendations",
                    request_type="course_recommendation",
                    response_time_ms=int((time.time() - start_time) * 1000),
                    success=False,
                    error_message=str(e),
                    metadata={"request_id": request_id},
                )

            raise

    async def stream_recommendations(
        self, request: RecommendationRequest, user: Optional[User] = None
    ) -> AsyncGenerator[str, None]:
        """Stream course recommendations as they are generated"""
        start_time = time.time()
        request_id = str(uuid4())

        try:
            logger.info(f"Starting streaming recommendation request {request_id}")

            # Step 1: Generate ideal course description
            yield "🔍 Analyzing your interests...\n\n"
            ideal_description = await self.llm_service.generate_course_description(
                request.query
            )

            # Step 2: Generate embedding
            yield "🧠 Understanding your preferences...\n\n"
            query_embedding = await self.vector_service.generate_embedding(
                ideal_description
            )

            # Step 3: Find similar courses
            yield "📚 Searching through course catalog...\n\n"
            course_filter = CourseFilter(levels=request.levels, include_inactive=False)

            similar_courses = await self.vector_service.search_similar_courses(
                query_embedding=query_embedding,
                filters=course_filter,
                limit=min(50, request.max_results * 3),
            )

            if not similar_courses:
                yield "❌ No courses found matching your criteria. Try adjusting your query or level preferences.\n"
                return

            yield f"✅ Found {len(similar_courses)} relevant courses! Generating personalized recommendations...\n\n"

            # Step 4: Stream LLM recommendations
            course_data = []
            for similar_course in similar_courses[: request.max_results * 2]:
                course_dict = {
                    "course_code": similar_course.course.course_code,
                    "title": similar_course.course.title,
                    "description": similar_course.course.description,
                    "level": similar_course.course.level,
                    "department": similar_course.course.department,
                    "similarity_score": similar_course.similarity_score,
                }
                course_data.append(course_dict)

            # Stream the recommendation generation
            async for chunk in self.llm_service.stream_recommendations_text(
                query=request.query, similar_courses=course_data
            ):
                yield chunk

            # Record usage
            if user:
                await self.usage_service.record_request(
                    user_id=user.id,
                    endpoint="recommendations",
                    request_type="streaming_course_recommendation",
                    response_time_ms=int((time.time() - start_time) * 1000),
                    success=True,
                    metadata={
                        "query_length": len(request.query),
                        "results_found": len(similar_courses),
                        "levels_requested": request.levels,
                        "request_id": request_id,
                    },
                )

        except Exception as e:
            logger.error(
                f"Error in streaming recommendation request {request_id}: {e}",
                exc_info=True,
            )
            yield f"\n\n❌ Error generating recommendations: {str(e)}"

            # Record error usage
            if user:
                await self.usage_service.record_request(
                    user_id=user.id,
                    endpoint="recommendations",
                    request_type="streaming_course_recommendation",
                    response_time_ms=int((time.time() - start_time) * 1000),
                    success=False,
                    error_message=str(e),
                    metadata={"request_id": request_id},
                )

    async def get_course_details(self, course_id: str) -> Optional[dict]:
        """Get detailed information about a specific course"""
        try:
            course = await self.course_repository.get_course_by_id(course_id)
            if not course:
                return None

            # Get embedding info if available
            course_embedding = await self.course_repository.get_course_embedding(
                course_id
            )

            return {
                "course": course.dict(),
                "has_embedding": course_embedding is not None,
                "embedding_model": (
                    course_embedding.embedding_model if course_embedding else None
                ),
                "embedding_created_at": (
                    course_embedding.embedding_created_at if course_embedding else None
                ),
            }

        except Exception as e:
            logger.error(f"Error getting course details for {course_id}: {e}")
            return None

    async def search_courses(
        self, query: str, filters: Optional[CourseFilter] = None, limit: int = 20
    ) -> List[dict]:
        """Search courses by text query"""
        try:
            # Text-based search through repository
            courses = await self.course_repository.search_courses(
                query=query, filters=filters
            )

            # Convert to dict format
            results = []
            for course in courses[:limit]:
                results.append(
                    {
                        "id": course.id,
                        "course_code": course.course_code,
                        "title": course.title,
                        "description": course.description,
                        "level": course.level,
                        "department": course.department,
                        "credits": course.credits,
                        "is_active": course.is_active,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Error searching courses: {e}")
            return []

    async def get_similar_courses(
        self, course_id: str, limit: int = 10
    ) -> List[SimilarCourse]:
        """Find courses similar to a given course"""
        try:
            # Get the source course embedding
            course_embedding = await self.course_repository.get_course_embedding(
                course_id
            )
            if not course_embedding:
                logger.warning(f"No embedding found for course {course_id}")
                return []

            # Find similar courses
            similar_courses = await self.vector_service.search_similar_courses(
                query_embedding=course_embedding.embedding,
                limit=limit + 1,  # +1 to exclude the source course
            )

            # Filter out the source course
            filtered_courses = [
                course for course in similar_courses if course.course.id != course_id
            ]

            return filtered_courses[:limit]

        except Exception as e:
            logger.error(f"Error finding similar courses for {course_id}: {e}")
            return []

    async def explain_course_relevance(
        self, course_id: str, user_query: str
    ) -> Optional[str]:
        """Explain why a course is relevant to a user's interests"""
        try:
            course = await self.course_repository.get_course_by_id(course_id)
            if not course:
                return None

            course_dict = {
                "course_code": course.course_code,
                "title": course.title,
                "description": course.description,
            }

            explanation = await self.llm_service.explain_recommendation(
                course=course_dict, user_query=user_query
            )

            return explanation

        except Exception as e:
            logger.error(f"Error explaining course relevance: {e}")
            return None

    async def get_recommendation_stats(self) -> dict:
        """Get statistics about the recommendation system"""
        try:
            # Get vector collection stats
            vector_stats = await self.vector_service.get_collection_stats()

            # Get course repository stats
            total_courses = await self.course_repository.get_course_count()
            active_courses = await self.course_repository.get_course_count(
                CourseFilter(include_inactive=False)
            )

            # Get all course embeddings
            all_embeddings = await self.course_repository.get_all_course_embeddings()

            return {
                "total_courses": total_courses,
                "active_courses": active_courses,
                "courses_with_embeddings": len(all_embeddings),
                "vector_stats": vector_stats,
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting recommendation stats: {e}")
            return {"error": str(e)}