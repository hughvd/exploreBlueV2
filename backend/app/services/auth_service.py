# services/auth_service.py
"""
Authentication service implementation
"""
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import uuid4
import logging

from .interfaces.auth_interface import AuthServiceInterface
from .interfaces.cache_interface import CacheServiceInterface
from ..models.user import User, UserSession, AuthProvider, UserRole
from ..repositories.interfaces.user_repository import UserRepositoryInterface
from ..core.config import BaseSettings

logger = logging.getLogger(__name__)


class AuthService(AuthServiceInterface):
    """Concrete implementation of authentication service"""

    def __init__(
        self,
        settings: BaseSettings,
        user_repository: UserRepositoryInterface,
        cache_service: CacheServiceInterface,
    ):
        self.settings = settings
        self.user_repository = user_repository
        self.cache_service = cache_service

    async def authenticate_user(
        self, token: str, auth_provider: Optional[AuthProvider] = None
    ) -> Optional[User]:
        """Authenticate user with given token and provider"""
        try:
            # For development/testing, support simple user creation
            if self.settings.environment.value in ["development", "testing"]:
                return await self._authenticate_dev_user(token)

            # Check cache first
            cache_key = f"auth:token:{hashlib.md5(token.encode()).hexdigest()}"
            cached_user = await self.cache_service.get(cache_key)
            if cached_user:
                return User(**cached_user)

            # Decode JWT token
            try:
                payload = jwt.decode(
                    token, self.settings.secret_key, algorithms=["HS256"]
                )
                user_id = payload.get("sub")
                if not user_id:
                    return None

                user = await self.user_repository.get_user_by_id(user_id)
                if user and user.is_active:
                    # Cache the user for a short time
                    await self.cache_service.set(
                        cache_key, user.dict(), expire=timedelta(minutes=15)
                    )
                    return user

            except jwt.InvalidTokenError:
                logger.warning(f"Invalid JWT token")
                return None

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    async def _authenticate_dev_user(self, token: str) -> Optional[User]:
        """Simple authentication for development"""
        # In development, create users on the fly for testing
        if token.startswith("dev_"):
            user_id = token.replace("dev_", "")

            # Check if user exists
            user = await self.user_repository.get_user_by_id(user_id)
            if user:
                return user

            # Create new dev user
            user = User(
                id=user_id,
                username=user_id,
                email=f"{user_id}@dev.local",
                full_name=f"Dev User {user_id}",
                role=UserRole.STUDENT,
                department="computer_science",
                auth_provider=AuthProvider.LOCAL,
                is_active=True,
                is_verified=True,
            )

            return await self.user_repository.create_user(user)

        return None

    async def create_session(self, user: User) -> UserSession:
        """Create a new user session"""
        session_id = str(uuid4())
        expires_at = datetime.utcnow() + timedelta(
            minutes=self.settings.access_token_expire_minutes
        )

        # Create JWT token
        token_payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "exp": expires_at,
        }

        access_token = jwt.encode(
            token_payload, self.settings.secret_key, algorithm="HS256"
        )

        session = UserSession(
            user_id=user.id,
            session_id=session_id,
            auth_token=access_token,
            expires_at=expires_at,
        )

        # Store session
        created_session = await self.user_repository.create_session(session)

        # Update last login
        await self.user_repository.update_last_login(user.id)

        return created_session

    async def validate_session(self, session_id: str) -> Optional[UserSession]:
        """Validate an existing session"""
        session = await self.user_repository.get_session(session_id)
        if not session:
            return None

        # Check if session is expired
        if session.expires_at < datetime.utcnow():
            await self.user_repository.delete_session(session_id)
            return None

        return session

    async def revoke_session(self, session_id: str) -> bool:
        """Revoke a user session"""
        return await self.user_repository.delete_session(session_id)

    async def get_user_permissions(self, user: User) -> List[str]:
        """Get user permissions based on role and context"""
        permissions = ["read:courses", "read:recommendations"]

        if user.role in [UserRole.STUDENT, UserRole.GRADUATE_STUDENT]:
            permissions.extend(["create:recommendations", "read:own_usage"])

        if user.role == UserRole.FACULTY:
            permissions.extend(
                ["create:recommendations", "read:own_usage", "read:department_usage"]
            )

        if user.role == UserRole.ADMIN:
            permissions.extend(
                [
                    "create:recommendations",
                    "read:usage",
                    "read:analytics",
                    "manage:users",
                    "manage:courses",
                    "manage:system",
                ]
            )

        return permissions
