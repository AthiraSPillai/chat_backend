"""
Authentication API dependencies for FastAPI Azure Backend.

This module provides dependency injection functions for authentication-related operations.
"""

from typing import Optional, Annotated, Dict, Any
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

from config import settings
from services.auth import get_user_by_userid, verify_token, get_user_by_username
from api.auth.schema import UserInDB, TokenPayload

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    scopes={
        "admin": "Full access to all resources",
        "user": "Access to user resources",
    },
)


async def get_current_user(
    security_scopes: SecurityScopes,
    token: Annotated[str, Depends(oauth2_scheme)]
) -> UserInDB:
    """
    Dependency to get the current authenticated user from a JWT token.
    
    Args:
        security_scopes: Security scopes required for the endpoint
        token: JWT token from the Authorization header
        
    Returns:
        UserInDB: The authenticated user
        
    Raises:
        HTTPException: If the token is invalid or the user doesn't have the required scopes
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    print("authenticate_value", authenticate_value)
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    # Verify the token and get the payload
    try:
        payload = await verify_token(token, "access")
        print(">>>>>",payload)
        user_id: str = payload.sub
        print("user_id", user_id,"=========")
        if user_id is None:
            raise credentials_exception
        token_scopes = payload.role.split()
    except Exception:
        raise credentials_exception
    
    # Get the user from the database
    user = await get_user_by_userid(user_id)
    print("user", user)
    if user is None:
        raise credentials_exception
    
    # Check if the user has at least one of the required scopes
    if security_scopes.scopes:
        if not any(scope in token_scopes or scope == user.role for scope in security_scopes.scopes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    
    return user


async def get_current_active_user(
    current_user: Annotated[UserInDB, Depends(get_current_user)]
) -> UserInDB:
    """
    Dependency to get the current active user.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        UserInDB: The authenticated active user
        
    Raises:
        HTTPException: If the user is inactive
    """
    print("__________", current_user)
    if not current_user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# Role-based security dependencies
async def get_admin_user(
    current_user: Annotated[UserInDB, Security(get_current_active_user, scopes=["admin"])]
) -> UserInDB:
    """
    Dependency to get the current admin user.
    
    Args:
        current_user: The authenticated user with admin scope
        
    Returns:
        UserInDB: The authenticated admin user
    """
    return current_user


async def get_regular_user(
    current_user: Annotated[UserInDB, Security(get_current_active_user, scopes=["user"])]
) -> UserInDB:
    """
    Dependency to get the current regular user.
    
    Args:
        current_user: The authenticated user with user scope
        
    Returns:
        UserInDB: The authenticated regular user
    """
    return current_user



async def get_current_user_from_token(request: Request) -> UserInDB:
    """
    Extracts and validates the JWT token from the request, returning the user.
    This is a simplified version for middleware, assuming token is in Authorization header.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = request.headers.get("Authorization")
    if not token or not token.startswith("Bearer "):
        raise credentials_exception
    
    token = token.split(" ")[1]

    try:
        payload = await verify_token(token, "access")
        print(payload)
        user_id: str = payload.sub
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    
    user = await get_user_by_userid(user_id)
    if user is None:
        raise credentials_exception
    
    return user


