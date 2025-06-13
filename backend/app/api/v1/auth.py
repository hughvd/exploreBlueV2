# api/v1/auth.py
"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from typing import Optional
import logging

from ...core.dependencies import (
    get_auth_service,
    get_current_user,
    get_current_user_optional,
    get_logging_context,
)
from ...models.user import User
from ...models.requests import AuthRequest, AuthResponse
from ...services.interfaces.auth_interface import AuthServiceInterface

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer()


@router.post("/login", response_model=AuthResponse)
async def login(
    auth_request: AuthRequest,
    auth_service: AuthServiceInterface = Depends(get_auth_service),
    logging_context: dict = Depends(get_logging_context),
):
    """
    Authenticate user and create session

    For development, you can use tokens like 'dev_student1', 'dev_faculty1', 'dev_admin'
    """
    try:
        logger.info(
            f"Login attempt for user: {auth_request.username}", extra=logging_context
        )

        # For development, support simple token-based auth
        if auth_request.token:
            user = await auth_service.authenticate_user(
                token=auth_request.token, auth_provider=None
            )
        else:
            # In production, this would handle username/password auth
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token authentication required for development",
            )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        # Create session
        session = await auth_service.create_session(user)

        # Get user permissions
        permissions = await auth_service.get_user_permissions(user)

        logger.info(
            f"Successful login for user: {user.username}", extra=logging_context
        )

        return AuthResponse(
            access_token=session.auth_token,
            token_type="bearer",
            expires_in=3600,  # 1 hour
            user=user,
            permissions=permissions,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", extra=logging_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    auth_service: AuthServiceInterface = Depends(get_auth_service),
    logging_context: dict = Depends(get_logging_context),
):
    """Logout current user and revoke session"""
    try:
        # In a real implementation, we'd get the session ID from the token
        # For now, just return success
        logger.info(f"Logout for user: {current_user.username}", extra=logging_context)

        return {"message": "Successfully logged out"}

    except Exception as e:
        logger.error(f"Logout error: {e}", extra=logging_context)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
        )


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.get("/permissions")
async def get_user_permissions(
    current_user: User = Depends(get_current_user),
    auth_service: AuthServiceInterface = Depends(get_auth_service),
):
    """Get current user's permissions"""
    try:
        permissions = await auth_service.get_user_permissions(current_user)

        return {"user_id": current_user.id, "permissions": permissions}

    except Exception as e:
        logger.error(f"Error getting permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permissions",
        )
