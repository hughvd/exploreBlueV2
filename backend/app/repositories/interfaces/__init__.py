# repositories/interfaces/__init__.py
"""
Repository interfaces package
"""
from .user_repository import UserRepositoryInterface
from .course_repository import CourseRepositoryInterface
from .usage_repository import UsageRepositoryInterface

__all__ = [
    "UserRepositoryInterface",
    "CourseRepositoryInterface",
    "UsageRepositoryInterface",
]
