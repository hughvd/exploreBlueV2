# repositories/interfaces/user_repository.py
"""
User repository interface
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
from ...models.user import User, UserSession, UsageRecord


class UserRepositoryInterface(ABC):
    """Abstract interface for user data operations"""

    @abstractmethod
    async def create_user(self, user: User) -> User:
        """Create a new user"""
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass

    @abstractmethod
    async def get_user_by_external_id(
        self, external_id: str, auth_provider: str
    ) -> Optional[User]:
        """Get user by external ID from auth provider"""
        pass

    @abstractmethod
    async def update_user(
        self, user_id: str, updates: Dict[str, Any]
    ) -> Optional[User]:
        """Update user information"""
        pass

    @abstractmethod
    async def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        pass

    @abstractmethod
    async def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[User]:
        """List users with pagination and filtering"""
        pass

    @abstractmethod
    async def get_users_by_department(self, department: str) -> List[User]:
        """Get all users in a specific department"""
        pass

    @abstractmethod
    async def get_users_by_role(self, role: str) -> List[User]:
        """Get all users with a specific role"""
        pass

    @abstractmethod
    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        pass

    # Session management
    @abstractmethod
    async def create_session(self, session: UserSession) -> UserSession:
        """Create a user session"""
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        pass

    @abstractmethod
    async def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user"""
        pass

    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        pass
