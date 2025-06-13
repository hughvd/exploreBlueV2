# services/vector_service.py
"""
Vector operations service implementation
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
import logging
import asyncio
from functools import lru_cache
import hashlib

from .interfaces.vector_interface import VectorServiceInterface
from .interfaces.cache_interface import CacheServiceInterface
from ..models.course import Course, CourseEmbedding, CourseFilter, SimilarCourse
from ..core.config import BaseSettings

logger = logging.getLogger(__name__)


class VectorService(VectorServiceInterface):
    """Concrete implementation of vector operations service"""

    def __init__(self, settings: BaseSettings, cache_service: CacheServiceInterface):
        self.settings = settings
        self.cache_service = cache_service
        self._embeddings_cache = {}
        self._courses_data = None
        self._embedding_lock = asyncio.Lock()

        # Initialize OpenAI client for embeddings
        self._init_openai_client()

    def _init_openai_client(self):
        """Initialize OpenAI client for embedding generation"""
        try:
            from openai import AsyncAzureOpenAI

            self.openai_client = AsyncAzureOpenAI(
                api_key=self.settings.openai_api_key,
                api_version=self.settings.openai_api_version,
                azure_endpoint=self.settings.openai_api_base,
                organization=self.settings.openai_organization_id,
            )
        except ImportError:
            logger.error("OpenAI client not available")
            self.openai_client = None

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")

        # Check cache first
        text_hash = hashlib.md5(text.encode()).hexdigest()
        cache_key = f"embedding:{text_hash}"

        cached_embedding = await self.cache_service.get(cache_key)
        if cached_embedding:
            return cached_embedding

        try:
            async with self._embedding_lock:
                response = await self.openai_client.embeddings.create(
                    input=[text], model=self.settings.embedding_model
                )
                embedding = response.data[0].embedding

                # Cache the embedding
                await self.cache_service.set(
                    cache_key, embedding, expire=timedelta(hours=24)
                )

                return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def store_course_embedding(
        self, course: Course, embedding: List[float]
    ) -> bool:
        """Store course embedding in vector database"""
        try:
            course_embedding = CourseEmbedding(
                course=course,
                embedding=embedding,
                embedding_model=self.settings.embedding_model,
            )

            # For now, store in memory cache
            # In production, this would go to a vector database
            cache_key = f"course_embedding:{course.id}"
            await self.cache_service.set(
                cache_key, course_embedding.dict(), expire=timedelta(days=7)
            )

            return True

        except Exception as e:
            logger.error(f"Error storing course embedding: {e}")
            return False

    async def search_similar_courses(
        self,
        query_embedding: List[float],
        filters: Optional[CourseFilter] = None,
        limit: int = 50,
    ) -> List[SimilarCourse]:
        """Find similar courses based on embedding"""
        try:
            # Load course data if not already loaded
            if self._courses_data is None:
                await self._load_course_data()

            if self._courses_data is None or len(self._courses_data) == 0:
                return []

            # Apply filters
            filtered_courses = self._apply_filters(self._courses_data, filters)

            if len(filtered_courses) == 0:
                return []

            # Calculate similarities efficiently
            similarities = await self._calculate_similarities(
                query_embedding, filtered_courses
            )

            # Get top similar courses
            top_indices = np.argsort(similarities)[-limit:][::-1]

            similar_courses = []
            for idx in top_indices:
                if similarities[idx] > 0.5:  # Minimum similarity threshold
                    course_data = filtered_courses.iloc[idx]
                    course = Course(
                        id=course_data["id"],
                        course_code=course_data["course"],
                        title=course_data["title"],
                        description=course_data["description"],
                        level=course_data["level"],
                        department=course_data.get("department", "Unknown"),
                    )

                    similar_course = SimilarCourse(
                        course=course, similarity_score=float(similarities[idx])
                    )
                    similar_courses.append(similar_course)

            return similar_courses

        except Exception as e:
            logger.error(f"Error searching similar courses: {e}")
            return []

    async def _load_course_data(self):
        """Load course data from embeddings file"""
        try:
            # In development, load from the original embeddings.pkl
            # In production, this would come from a vector database
            import pandas as pd
            import os

            embeddings_path = "embeddings.pkl"
            if os.path.exists(embeddings_path):
                self._courses_data = pd.read_pickle(embeddings_path)
                logger.info(f"Loaded {len(self._courses_data)} courses with embeddings")
            else:
                logger.warning("No embeddings file found, using empty dataset")
                self._courses_data = pd.DataFrame()

        except Exception as e:
            logger.error(f"Error loading course data: {e}")
            self._courses_data = pd.DataFrame()

    def _apply_filters(
        self, courses_df: pd.DataFrame, filters: Optional[CourseFilter]
    ) -> pd.DataFrame:
        """Apply filters to course dataframe"""
        if filters is None:
            return courses_df

        filtered_df = courses_df.copy()

        # Filter by levels
        if filters.levels:
            filtered_df = filtered_df[filtered_df["level"].isin(filters.levels)]

        # Filter by departments
        if filters.departments:
            filtered_df = filtered_df[
                filtered_df["department"].isin(filters.departments)
            ]

        # Filter by active status
        if not filters.include_inactive:
            if "is_active" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["is_active"] == True]

        return filtered_df

    async def _calculate_similarities(
        self, query_embedding: List[float], courses_df: pd.DataFrame
    ) -> np.ndarray:
        """Calculate cosine similarities efficiently"""
        if len(courses_df) == 0:
            return np.array([])

        # Convert embeddings to numpy array
        embeddings_matrix = np.array(courses_df["embedding"].tolist())
        query_vector = np.array(query_embedding)

        # Calculate cosine similarities using vectorized operations
        dot_products = np.dot(embeddings_matrix, query_vector)
        norms = np.linalg.norm(embeddings_matrix, axis=1) * np.linalg.norm(query_vector)

        # Avoid division by zero
        similarities = np.divide(
            dot_products, norms, out=np.zeros_like(dot_products), where=norms != 0
        )

        return similarities

    async def update_course_embedding(
        self, course_id: str, embedding: List[float]
    ) -> bool:
        """Update existing course embedding"""
        try:
            cache_key = f"course_embedding:{course_id}"
            existing_data = await self.cache_service.get(cache_key)

            if existing_data:
                existing_data["embedding"] = embedding
                existing_data["embedding_created_at"] = datetime.utcnow().isoformat()

                await self.cache_service.set(
                    cache_key, existing_data, expire=timedelta(days=7)
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Error updating course embedding: {e}")
            return False

    async def delete_course_embedding(self, course_id: str) -> bool:
        """Delete course embedding"""
        try:
            cache_key = f"course_embedding:{course_id}"
            return await self.cache_service.delete(cache_key)
        except Exception as e:
            logger.error(f"Error deleting course embedding: {e}")
            return False

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get vector collection statistics"""
        try:
            if self._courses_data is None:
                await self._load_course_data()

            if self._courses_data is None:
                return {"error": "No course data available"}

            stats = {
                "total_courses": len(self._courses_data),
                "embedding_dimension": (
                    len(self._courses_data.iloc[0]["embedding"])
                    if len(self._courses_data) > 0
                    else 0
                ),
                "departments": (
                    self._courses_data["department"].nunique()
                    if "department" in self._courses_data.columns
                    else 0
                ),
                "levels": (
                    sorted(self._courses_data["level"].unique().tolist())
                    if "level" in self._courses_data.columns
                    else []
                ),
                "last_updated": datetime.utcnow().isoformat(),
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
