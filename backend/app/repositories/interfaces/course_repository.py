# repositories/interfaces/course_repository.py
"""
Course repository interface
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from ...models.course import Course, CourseEmbedding, CourseFilter


class CourseRepositoryInterface(ABC):
    """Abstract interface for course data operations"""

    @abstractmethod
    async def create_course(self, course: Course) -> Course:
        """Create a new course"""
        pass

    @abstractmethod
    async def get_course_by_id(self, course_id: str) -> Optional[Course]:
        """Get course by ID"""
        pass

    @abstractmethod
    async def get_course_by_code(self, course_code: str) -> Optional[Course]:
        """Get course by course code (e.g., EECS485)"""
        pass

    @abstractmethod
    async def update_course(
        self, course_id: str, updates: Dict[str, Any]
    ) -> Optional[Course]:
        """Update course information"""
        pass

    @abstractmethod
    async def delete_course(self, course_id: str) -> bool:
        """Delete a course"""
        pass

    @abstractmethod
    async def list_courses(
        self, limit: int = 100, offset: int = 0, filters: Optional[CourseFilter] = None
    ) -> List[Course]:
        """List courses with pagination and filtering"""
        pass

    @abstractmethod
    async def get_courses_by_department(self, department: str) -> List[Course]:
        """Get all courses in a specific department"""
        pass

    @abstractmethod
    async def get_courses_by_level(self, level: int) -> List[Course]:
        """Get all courses at a specific level"""
        pass

    @abstractmethod
    async def get_courses_by_levels(self, levels: List[int]) -> List[Course]:
        """Get all courses at specified levels"""
        pass

    @abstractmethod
    async def search_courses(
        self, query: str, filters: Optional[CourseFilter] = None
    ) -> List[Course]:
        """Search courses by text query"""
        pass

    @abstractmethod
    async def get_active_courses(self) -> List[Course]:
        """Get all active courses"""
        pass

    @abstractmethod
    async def bulk_update_courses(self, course_updates: List[Dict[str, Any]]) -> int:
        """Bulk update multiple courses"""
        pass

    @abstractmethod
    async def get_course_count(self, filters: Optional[CourseFilter] = None) -> int:
        """Get total count of courses matching filters"""
        pass

    # Embedding operations
    @abstractmethod
    async def store_course_embedding(self, course_embedding: CourseEmbedding) -> bool:
        """Store course embedding data"""
        pass

    @abstractmethod
    async def get_course_embedding(self, course_id: str) -> Optional[CourseEmbedding]:
        """Get course embedding by course ID"""
        pass

    @abstractmethod
    async def get_all_course_embeddings(self) -> List[CourseEmbedding]:
        """Get all course embeddings"""
        pass

    @abstractmethod
    async def update_course_embedding(
        self, course_id: str, embedding: List[float], model: str
    ) -> bool:
        """Update course embedding"""
        pass

    @abstractmethod
    async def delete_course_embedding(self, course_id: str) -> bool:
        """Delete course embedding"""
        pass
