# services/interfaces/llm_service.py
"""
Large Language Model service interface
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncGenerator


class LLMServiceInterface(ABC):
    """Abstract interface for LLM operations"""

    @abstractmethod
    async def generate_course_description(self, query: str) -> str:
        """Generate ideal course description based on user query"""
        pass

    @abstractmethod
    async def generate_recommendations_text(
        self, query: str, similar_courses: List[Dict[str, Any]]
    ) -> str:
        """Generate recommendation text based on query and similar courses"""
        pass

    @abstractmethod
    async def stream_recommendations_text(
        self, query: str, similar_courses: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Stream recommendation text generation"""
        pass

    @abstractmethod
    async def explain_recommendation(
        self, course: Dict[str, Any], user_query: str
    ) -> str:
        """Explain why a specific course was recommended"""
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding (may delegate to vector service)"""
        pass
