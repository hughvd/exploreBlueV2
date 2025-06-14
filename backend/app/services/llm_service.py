# services/llm_service.py
"""
Large Language Model service implementation
"""
import asyncio
from typing import List, Dict, Any, AsyncGenerator
import logging
from datetime import timedelta

from .interfaces.llm_interface import LLMServiceInterface
from .interfaces.cache_interface import CacheServiceInterface
from ..core.config import BaseSettings

logger = logging.getLogger(__name__)


class LLMService(LLMServiceInterface):
    """OpenAI/Azure OpenAI implementation of LLM service"""
    
    def __init__(
        self, 
        settings: BaseSettings,
        cache_service: CacheServiceInterface
    ):
        self.settings = settings
        self.cache_service = cache_service
        self._init_openai_client()
        
        # Concurrency control
        self.api_semaphore = asyncio.Semaphore(5)
    
    def _init_openai_client(self):
        """Initialize OpenAI client"""
        try:
            from openai import AsyncAzureOpenAI
            
            self.openai_client = AsyncAzureOpenAI(
                api_key=self.settings.openai_api_key,
                api_version=self.settings.openai_api_version,
                azure_endpoint=self.settings.openai_api_base,
                organization=self.settings.openai_organization_id
            )
        except ImportError:
            logger.error("OpenAI client not available")
            self.openai_client = None
    
    async def generate_course_description(self, query: str) -> str:
        """Generate ideal course description based on user query"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")
        
        # Check cache first
        cache_key = f"course_description:{hash(query)}"
        cached_result = await self.cache_service.get(cache_key)
        if cached_result:
            return cached_result
        
        system_prompt = """You will be given a request from a student at The University of Michigan to provide quality course recommendations. 
Generate a course description that would be most applicable to their request. In the course description, provide a list of topics as well as a 
general description of the course. Limit the description to be less than 200 words.

Student Request:
{query}"""
        
        messages = [
            {"role": "system", "content": system_prompt.format(query=query)},
            {"role": "user", "content": query}
        ]
        
        try:
            async with self.api_semaphore:
                response = await self.openai_client.chat.completions.create(
                    model=self.settings.generator_model,
                    messages=messages,
                    temperature=0,
                    max_tokens=300,
                    stream=False
                )
                
                description = response.choices[0].message.content
                
                # Cache the result
                await self.cache_service.set(
                    cache_key, 
                    description,
                    expire=timedelta(hours=6)
                )
                
                return description
                
        except Exception as e:
            logger.error(f"Error generating course description: {e}")
            raise
    
    async def generate_recommendations_text(
        self, 
        query: str, 
        similar_courses: List[Dict[str, Any]]
    ) -> str:
        """Generate recommendation text based on query and similar courses"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")
        
        # Format courses for the prompt
        course_string = "\n".join([
            f"{course['course_code']}: {course['title']}\n{course['description']}"
            for course in similar_courses
        ])
        
        system_prompt = f"""You are an expert academic advisor specializing in personalized course recommendations. 
When evaluating matches between student profiles and courses, prioritize direct relevance and career trajectory fit.

Context: Student Profile ({query})
Course Options: 
{course_string}

REQUIREMENTS:
- Return exactly 10 courses, ranked by relevance and fit
- Recommend ONLY courses listed in Course Options
- If a course is cross-listed, write the course number as "COURSEXXX (Cross-listed as COURSEYYY)"
- For each recommendation include:
  1. Course number (include cross-listed courses)
  2. Course name
  2. Two-sentence explanation focused on student's specific profile/goals
  3. Confidence level (High/Medium/Low)

FORMAT (Markdown):
1. **COURSEXXX: COURSE_TITLE**
Rationale: [Two clear sentences explaining fit]
Confidence: [Level]

2. [Next course...]

CONSTRAINTS:
- NO general academic advice
- NO mentions of prerequisites unless explicitly stated in course description
- NO suggestions outside provided course list
- NO mention of being an AI or advisor"""

        messages = [{"role": "system", "content": system_prompt}]
        
        try:
            async with self.api_semaphore:
                response = await self.openai_client.chat.completions.create(
                    model=self.settings.recommender_model,
                    messages=messages,
                    temperature=0,
                    max_tokens=1500,
                    stream=False
                )
                
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            raise
    
    async def stream_recommendations_text(
        self, 
        query: str, 
        similar_courses: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Stream recommendation text generation"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")
        
        # Format courses for the prompt (same as above)
        course_string = "\n".join([
            f"{course['course_code']}: {course['title']}\n{course['description']}"
            for course in similar_courses
        ])
        
        system_prompt = f"""You are an expert academic advisor specializing in personalized course recommendations. 
When evaluating matches between student profiles and courses, prioritize direct relevance and career trajectory fit.

Context: Student Profile ({query})
Course Options: 
{course_string}

REQUIREMENTS:
- Return exactly 10 courses, ranked by relevance and fit
- Recommend ONLY courses listed in Course Options
- For each recommendation include:
  1. Course number
  2. Course name
  2. Two-sentence explanation focused on student's specific profile/goals
  3. Confidence level (High/Medium/Low)

FORMAT (Markdown):
1. **COURSEXXX: COURSE_TITLE**
Rationale: [Two clear sentences explaining fit]
Confidence: [Level]

2. [Next course...]

CONSTRAINTS:
- NO general academic advice
- NO mentions of prerequisites unless explicitly stated in course description
- NO suggestions outside provided course list
- NO mention of being an AI or advisor"""

        messages = [{"role": "system", "content": system_prompt}]
        
        try:
            async with self.api_semaphore:
                response = await self.openai_client.chat.completions.create(
                    model=self.settings.recommender_model,
                    messages=messages,
                    temperature=0,
                    stream=True
                )
                
                async for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                        
        except Exception as e:
            logger.error(f"Error streaming recommendations: {e}")
            yield f"Error generating recommendation: {str(e)}"
    
    async def explain_recommendation(
        self, 
        course: Dict[str, Any], 
        user_query: str
    ) -> str:
        """Explain why a specific course was recommended"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")
        
        system_prompt = f"""Explain in 2-3 sentences why the course "{course['course_code']}: {course['title']}" 
is a good fit for a student interested in: "{user_query}".

Course Description: {course.get('description', 'No description available')}

Focus on specific connections between the student's interests and the course content."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Why is this course relevant for: {user_query}"}
        ]
        
        try:
            async with self.api_semaphore:
                response = await self.openai_client.chat.completions.create(
                    model=self.settings.generator_model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=150,
                    stream=False
                )
                
                return response.choices[0].message.content
                
        except Exception as e:
            logger.error(f"Error explaining recommendation: {e}")
            return "Unable to generate explanation at this time."
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding (delegates to vector service typically)"""
        if not self.openai_client:
            raise RuntimeError("OpenAI client not initialized")
        
        try:
            async with self.api_semaphore:
                response = await self.openai_client.embeddings.create(
                    input=[text],
                    model=self.settings.embedding_model
                )
                
                return response.data[0].embedding
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
