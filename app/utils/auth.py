"""Authentication utilities and dependencies."""
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import structlog

from app.database import get_db
from app.services.auth import AuthService
from app.models.user import User
from app.config import settings

logger = structlog.get_logger()

security = HTTPBearer(auto_error=False)
auth_service = AuthService()


def verify_export_api_key(api_key: str = Header(..., alias="X-Export-API-Key")) -> bool:
    """
    Verify static API key for external service access to exports.

    Args:
        api_key: The API key from the request header

    Returns:
        bool: True if key is valid

    Raises:
        HTTPException: If key is invalid or feature is disabled
    """
    if not settings.export_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="External API access is disabled"
        )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Export API key required"
        )

    if not settings.export_api_keys:
        logger.warning("Export API key provided but no keys configured")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No export API keys configured"
        )

    if api_key not in settings.export_api_keys:
        logger.warning("Invalid export API key provided", provided_key_hash=hash(api_key))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid export API key"
        )

    logger.info("Export API key authenticated successfully")
    return True


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token or API key.
    
    Supports two authentication methods:
    1. Bearer token in Authorization header
    2. API key in X-API-Key header
    """
    user = None
    
    # Try API key authentication first
    if api_key:
        user = await auth_service.authenticate_api_key(db, api_key)
        if user:
            return user
    
    # Try JWT token authentication
    if credentials and credentials.credentials:
        token = credentials.credentials
        user = await auth_service.get_current_user(db, token)
        if user:
            return user
    
    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    Used for endpoints that support both authenticated and anonymous access.
    """
    try:
        return await get_current_user(credentials, api_key, db)
    except HTTPException:
        return None


def require_permission(user: User, permission: str, resource: Optional[str] = None):
    """
    Require user to have specific permission.
    
    Args:
        user: Authenticated user
        permission: Required permission (read, write, admin, etc.)
        resource: Optional resource identifier
    
    Raises:
        HTTPException: If user doesn't have required permission
    """
    if not auth_service.check_permission(user, permission, resource):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions: {permission} required"
        )


def require_admin(user: User):
    """
    Require user to be an administrator.
    
    Args:
        user: Authenticated user
    
    Raises:
        HTTPException: If user is not an admin
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required"
        )


def require_active_user(user: User):
    """
    Require user account to be active.
    
    Args:
        user: Authenticated user
    
    Raises:
        HTTPException: If user account is not active
    """
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
