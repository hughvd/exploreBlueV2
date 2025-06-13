# repositories/memory_user_repository.py
"""
In-memory user repository implementation for development/testing
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import threading

from .interfaces.user_repository import UserRepositoryInterface
from ..models.user import User, UserSession, UsageRecord


class MemoryUserRepository(UserRepositoryInterface):
    """In-memory implementation of user repository"""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, UserSession] = {}
        self.usage_records: List[UsageRecord] = []
        self.lock = threading.RLock()

        # Create some default users for development
        self._create_default_users()

    def _create_default_users(self):
        """Create default users for development"""
        from ..models.user import UserRole, AuthProvider

        default_users = [
            User(
                id="admin",
                username="admin",
                email="admin@dev.local",
                full_name="Admin User",
                role=UserRole.ADMIN,
                department="administration",
                auth_provider=AuthProvider.LOCAL,
                is_active=True,
                is_verified=True,
            ),
            User(
                id="student1",
                username="student1",
                email="student1@dev.local",
                full_name="Test Student",
                role=UserRole.STUDENT,
                department="computer_science",
                auth_provider=AuthProvider.LOCAL,
                is_active=True,
                is_verified=True,
            ),
            User(
                id="faculty1",
                username="faculty1",
                email="faculty1@dev.local",
                full_name="Test Faculty",
                role=UserRole.FACULTY,
                department="computer_science",
                auth_provider=AuthProvider.LOCAL,
                is_active=True,
                is_verified=True,
            ),
        ]

        for user in default_users:
            self.users[user.id] = user

    async def create_user(self, user: User) -> User:
        """Create a new user"""
        with self.lock:
            if user.id in self.users:
                raise ValueError(f"User with ID {user.id} already exists")

            self.users[user.id] = user
            return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        with self.lock:
            return self.users.get(user_id)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        with self.lock:
            for user in self.users.values():
                if user.username == username:
                    return user
            return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        with self.lock:
            for user in self.users.values():
                if user.email == email:
                    return user
            return None

    async def get_user_by_external_id(
        self, external_id: str, auth_provider: str
    ) -> Optional[User]:
        """Get user by external ID from auth provider"""
        with self.lock:
            for user in self.users.values():
                if (
                    user.external_id == external_id
                    and user.auth_provider.value == auth_provider
                ):
                    return user
            return None

    async def update_user(
        self, user_id: str, updates: Dict[str, Any]
    ) -> Optional[User]:
        """Update user information"""
        with self.lock:
            if user_id not in self.users:
                return None

            user = self.users[user_id]

            # Update fields
            for field, value in updates.items():
                if hasattr(user, field):
                    setattr(user, field, value)

            return user

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        with self.lock:
            if user_id in self.users:
                del self.users[user_id]
                # Also delete user's sessions
                sessions_to_delete = [
                    session_id
                    for session_id, session in self.sessions.items()
                    if session.user_id == user_id
                ]
                for session_id in sessions_to_delete:
                    del self.sessions[session_id]
                return True
            return False

    async def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[User]:
        """List users with pagination and filtering"""
        with self.lock:
            users_list = list(self.users.values())

            # Apply filters
            if filters:
                if "role" in filters:
                    users_list = [u for u in users_list if u.role == filters["role"]]
                if "department" in filters:
                    users_list = [
                        u for u in users_list if u.department == filters["department"]
                    ]
                if "is_active" in filters:
                    users_list = [
                        u for u in users_list if u.is_active == filters["is_active"]
                    ]

            # Apply pagination
            return users_list[offset : offset + limit]

    async def get_users_by_department(self, department: str) -> List[User]:
        """Get all users in a specific department"""
        with self.lock:
            return [
                user for user in self.users.values() if user.department == department
            ]

    async def get_users_by_role(self, role: str) -> List[User]:
        """Get all users with a specific role"""
        with self.lock:
            return [user for user in self.users.values() if user.role.value == role]

    async def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        with self.lock:
            if user_id in self.users:
                self.users[user_id].last_login = datetime.utcnow()
                return True
            return False

    # Session management
    async def create_session(self, session: UserSession) -> UserSession:
        """Create a user session"""
        with self.lock:
            self.sessions[session.session_id] = session
            return session

    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by ID"""
        with self.lock:
            return self.sessions.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False

    async def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user"""
        with self.lock:
            sessions_to_delete = [
                session_id
                for session_id, session in self.sessions.items()
                if session.user_id == user_id
            ]

            for session_id in sessions_to_delete:
                del self.sessions[session_id]

            return len(sessions_to_delete)

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        with self.lock:
            now = datetime.utcnow()
            expired_sessions = [
                session_id
                for session_id, session in self.sessions.items()
                if session.expires_at < now
            ]

            for session_id in expired_sessions:
                del self.sessions[session_id]

            return len(expired_sessions)
