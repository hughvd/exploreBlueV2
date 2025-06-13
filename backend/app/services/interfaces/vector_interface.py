# services/interfaces/vector_service.py
"""
Vector operations service interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ...models.course import Course, CourseEmbedding, CourseFilter, SimilarCourse


class VectorServiceInterface(ABC):
    """Abstract interface for vector operations"""

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text"""
        pass

    @abstractmethod
    async def store_course_embedding(
        self, course: Course, embedding: List[float]
    ) -> bool:
        """Store course embedding in vector database"""
        pass

    @abstractmethod
    async def search_similar_courses(
        self,
        query_embedding: List[float],
        filters: Optional[CourseFilter] = None,
        limit: int = 50,
    ) -> List[SimilarCourse]:
        """Find similar courses based on embedding"""
        pass

    @abstractmethod
    async def update_course_embedding(
        self, course_id: str, embedding: List[float]
    ) -> bool:
        """Update existing course embedding"""
        pass

    @abstractmethod
    async def delete_course_embedding(self, course_id: str) -> bool:
        """Delete course embedding"""
        pass

    @abstractmethod
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get vector collection statistics"""
        pass
