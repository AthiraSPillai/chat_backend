"""
Authentication API routes for FastAPI Azure Backend.

This module defines routes for authentication-related operations.
"""

import datetime
from typing import Annotated
from integrations.azure_cosmos_db import delete_item
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from config import settings
from api.auth.schema import TokenResponse, UserResponse, UserCreate, RefreshTokenRequest
from api.auth.dependency import get_current_active_user, get_admin_user
from services.auth import (
    authenticate_user,
    create_tokens,
    refresh_access_token,
    create_user,
    get_user_by_username,
)
import jwt

from utils.response import SuccessResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> TokenResponse:
    """
    Authenticate user and return JWT tokens.
    
    Args:
        form_data: OAuth2 form with username and password
        
    Returns:
        TokenResponse: Access and refresh tokens
        
    Raises:
        HTTPException: If authentication fails
    """
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access and refresh tokens
    tokens = await create_tokens(user.id, user.username, user.role)
    
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_request: RefreshTokenRequest) -> TokenResponse:
    """
    Refresh access token using a valid refresh token.
    
    Args:
        refresh_request: Refresh token request
        
    Returns:
        TokenResponse: New access and refresh tokens
        
    Raises:
        HTTPException: If the refresh token is invalid
    """
    tokens = await refresh_access_token(refresh_request.refresh_token)
    return tokens





async def decode_refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(
            refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    refresh_token: Annotated[str, Body(embed=True)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> SuccessResponse:
    """
    Logout user by revoking the refresh token.

    Steps:
    1. Decode refresh token, get `jti`.
    2. Delete the token record from active tokens container in Cosmos DB.
    """
    payload = await decode_refresh_token(refresh_token)

    jti = payload.get("jti")
    print("JTI:", jti)

    # Delete the active refresh token from Cosmos DB (revoke)
    deleted = await delete_item(settings.REFRESH_TOKEN_CONTAINER_NAME, jti, jti)
    print("Deleted token:", deleted)
    if not deleted:
        # Token not found or already revoked
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token not found or already revoked"
        )

    return SuccessResponse(message="Successfully logged out")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> UserResponse:
    """
    Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserResponse: Current user data
    """
    print("============Current User:", current_user)
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )
