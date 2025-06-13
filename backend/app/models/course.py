# models/course.py
"""
Course-related data models
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class Course(BaseModel):
    """Core course model"""

    id: str
    course_code: str  # e.g., "EECS485"
    title: str
    description: str
    level: int  # 100, 200, 300, etc.
    credits: Optional[int] = None
    department: str

    # Academic information
    prerequisites: List[str] = Field(default_factory=list)
    corequisites: List[str] = Field(default_factory=list)
    restrictions: List[str] = Field(default_factory=list)

    # Offering information
    offered_terms: List[str] = Field(
        default_factory=list
    )  # Fall, Winter, Spring, Summer
    instructors: List[str] = Field(default_factory=list)

    # Metadata
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    class Config:
        from_attributes = True


class CourseEmbedding(BaseModel):
    """Course with embedding data"""

    course: Course
    embedding: List[float]
    embedding_model: str
    embedding_created_at: datetime = Field(default_factory=datetime.utcnow)


class CourseFilter(BaseModel):
    """Filters for course search"""

    levels: Optional[List[int]] = None
    departments: Optional[List[str]] = None
    terms: Optional[List[str]] = None
    credit_range: Optional[tuple[int, int]] = None
    include_inactive: bool = False


class SimilarCourse(BaseModel):
    """Course with similarity score"""

    course: Course
    similarity_score: float
    relevance_explanation: Optional[str] = None
