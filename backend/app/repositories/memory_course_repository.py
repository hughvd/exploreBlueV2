# repositories/memory_course_repository.py
"""
In-memory course repository implementation for development/testing
"""
import pandas as pd
import os
from typing import Optional, List, Dict, Any
from datetime import datetime
import threading

from .interfaces.course_repository import CourseRepositoryInterface
from ..models.course import Course, CourseEmbedding, CourseFilter


class MemoryCourseRepository(CourseRepositoryInterface):
    """In-memory implementation of course repository"""

    def __init__(self):
        self.courses: Dict[str, Course] = {}
        self.course_embeddings: Dict[str, CourseEmbedding] = {}
        self.lock = threading.RLock()

        # Load courses from embeddings file if available
        self._load_courses_from_embeddings()

    def _load_courses_from_embeddings(self):
        """Load courses from the original embeddings.pkl file"""
        try:
            embeddings_path = "embeddings.pkl"
            if os.path.exists(embeddings_path):
                df = pd.read_pickle(embeddings_path)

                for idx, row in df.iterrows():
                    course_id = str(idx)
                    course = Course(
                        id=course_id,
                        course_code=row.get("course", f"COURSE{idx}"),
                        title=row.get("title", "Unknown Title"),
                        description=row.get("description", ""),
                        level=int(row.get("level", 100)),
                        department=row.get("department", "Unknown"),
                        is_active=True,
                    )

                    self.courses[course_id] = course

                    # Store embedding if available
                    if "embedding" in row and row["embedding"] is not None:
                        course_embedding = CourseEmbedding(
                            course=course,
                            embedding=row["embedding"],
                            embedding_model="text-embedding-ada-002",
                        )
                        self.course_embeddings[course_id] = course_embedding

                print(f"Loaded {len(self.courses)} courses from embeddings file")
            else:
                print("No embeddings file found, using empty course repository")
                self._create_sample_courses()

        except Exception as e:
            print(f"Error loading courses from embeddings: {e}")
            self._create_sample_courses()

    def _create_sample_courses(self):
        """Create some sample courses for development"""
        sample_courses = [
            Course(
                id="1",
                course_code="EECS485",
                title="Web Systems",
                description="Introduction to web application development and systems. Topics include client-server architecture, HTTP, HTML, CSS, JavaScript, databases, and web frameworks.",
                level=400,
                department="EECS",
                credits=4,
                is_active=True,
            ),
            Course(
                id="2",
                course_code="EECS280",
                title="Programming and Introductory Data Structures",
                description="Techniques and algorithm development and effective programming, top-down analysis, structured programming, testing and program correctness.",
                level=200,
                department="EECS",
                credits=4,
                is_active=True,
            ),
            Course(
                id="3",
                course_code="EECS445",
                title="Introduction to Machine Learning",
                description="Theory and implementation of state-of-the-art machine learning algorithms for large-scale real-world applications.",
                level=400,
                department="EECS",
                credits=3,
                is_active=True,
            ),
        ]

        for course in sample_courses:
            self.courses[course.id] = course

    async def create_course(self, course: Course) -> Course:
        """Create a new course"""
        with self.lock:
            if course.id in self.courses:
                raise ValueError(f"Course with ID {course.id} already exists")

            self.courses[course.id] = course
            return course

    async def get_course_by_id(self, course_id: str) -> Optional[Course]:
        """Get course by ID"""
        with self.lock:
            return self.courses.get(course_id)

    async def get_course_by_code(self, course_code: str) -> Optional[Course]:
        """Get course by course code"""
        with self.lock:
            for course in self.courses.values():
                if course.course_code == course_code:
                    return course
            return None

    async def update_course(
        self, course_id: str, updates: Dict[str, Any]
    ) -> Optional[Course]:
        """Update course information"""
        with self.lock:
            if course_id not in self.courses:
                return None

            course = self.courses[course_id]

            # Update fields
            for field, value in updates.items():
                if hasattr(course, field):
                    setattr(course, field, value)

            course.last_updated = datetime.utcnow()
            return course

    async def delete_course(self, course_id: str) -> bool:
        """Delete a course"""
        with self.lock:
            if course_id in self.courses:
                del self.courses[course_id]
                # Also delete course embedding if exists
                if course_id in self.course_embeddings:
                    del self.course_embeddings[course_id]
                return True
            return False

    async def list_courses(
        self, limit: int = 100, offset: int = 0, filters: Optional[CourseFilter] = None
    ) -> List[Course]:
        """List courses with pagination and filtering"""
        with self.lock:
            courses_list = list(self.courses.values())

            # Apply filters
            if filters:
                courses_list = self._apply_filter(courses_list, filters)

            # Apply pagination
            return courses_list[offset : offset + limit]

    def _apply_filter(
        self, courses: List[Course], filters: CourseFilter
    ) -> List[Course]:
        """Apply filters to course list"""
        filtered_courses = courses

        if filters.levels:
            filtered_courses = [
                c for c in filtered_courses if c.level in filters.levels
            ]

        if filters.departments:
            filtered_courses = [
                c for c in filtered_courses if c.department in filters.departments
            ]

        if not filters.include_inactive:
            filtered_courses = [c for c in filtered_courses if c.is_active]

        return filtered_courses

    async def get_courses_by_department(self, department: str) -> List[Course]:
        """Get all courses in a specific department"""
        with self.lock:
            return [
                course
                for course in self.courses.values()
                if course.department == department
            ]

    async def get_courses_by_level(self, level: int) -> List[Course]:
        """Get all courses at a specific level"""
        with self.lock:
            return [course for course in self.courses.values() if course.level == level]

    async def get_courses_by_levels(self, levels: List[int]) -> List[Course]:
        """Get all courses at specified levels"""
        with self.lock:
            return [
                course for course in self.courses.values() if course.level in levels
            ]

    async def get_active_courses(self) -> List[Course]:
        """Get all active courses"""
        with self.lock:
            return [course for course in self.courses.values() if course.is_active]

    async def bulk_update_courses(self, course_updates: List[Dict[str, Any]]) -> int:
        """Bulk update multiple courses"""
        with self.lock:
            updated_count = 0

            for update in course_updates:
                course_id = update.get("id")
                if course_id and course_id in self.courses:
                    course = self.courses[course_id]

                    for field, value in update.items():
                        if field != "id" and hasattr(course, field):
                            setattr(course, field, value)

                    course.last_updated = datetime.utcnow()
                    updated_count += 1

            return updated_count

    async def get_course_count(self, filters: Optional[CourseFilter] = None) -> int:
        """Get total count of courses matching filters"""
        with self.lock:
            courses_list = list(self.courses.values())

            if filters:
                courses_list = self._apply_filter(courses_list, filters)

            return len(courses_list)

    # Embedding operations
    async def store_course_embedding(self, course_embedding: CourseEmbedding) -> bool:
        """Store course embedding data"""
        with self.lock:
            self.course_embeddings[course_embedding.course.id] = course_embedding
            return True

    async def get_course_embedding(self, course_id: str) -> Optional[CourseEmbedding]:
        """Get course embedding by course ID"""
        with self.lock:
            return self.course_embeddings.get(course_id)

    async def get_all_course_embeddings(self) -> List[CourseEmbedding]:
        """Get all course embeddings"""
        with self.lock:
            return list(self.course_embeddings.values())

    async def update_course_embedding(
        self, course_id: str, embedding: List[float], model: str
    ) -> bool:
        """Update course embedding"""
        with self.lock:
            if course_id in self.course_embeddings:
                course_embedding = self.course_embeddings[course_id]
                course_embedding.embedding = embedding
                course_embedding.embedding_model = model
                course_embedding.embedding_created_at = datetime.utcnow()
                return True
            return False

    async def delete_course_embedding(self, course_id: str) -> bool:
        """Delete course embedding"""
        with self.lock:
            if course_id in self.course_embeddings:
                del self.course_embeddings[course_id]
                return True
            return False
