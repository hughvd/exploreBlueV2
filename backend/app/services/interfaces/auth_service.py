# services/interfaces/auth_service.py
"""
Authentication service interface
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from ...models.user import User, UserSession, AuthProvider


class AuthServiceInterface(ABC):
    """Abstract interface for authentication services"""

    @abstractmethod
    async def authenticate_user(
        self, token: str, auth_provider: AuthProvider
    ) -> Optional[User]:
        """Authenticate user with given token and provider"""
        pass

    @abstractmethod
    async def create_session(self, user: User) -> UserSession:
        """Create a new user session"""
        pass

    @abstractmethod
    async def validate_session(self, session_id: str) -> Optional[UserSession]:
        """Validate an existing session"""
        pass

    @abstractmethod
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a user session"""
        pass

    @abstractmethod
    async def get_user_permissions(self, user: User) -> List[str]:
        """Get user permissions based on role and context"""
        pass
