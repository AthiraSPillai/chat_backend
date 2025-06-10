"""
Authentication service for FastAPI Azure Backend.

This module provides functions for user authentication and token management.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from pydantic.json import pydantic_encoder

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from config import settings
from api.auth.schema import UserInDB, TokenResponse, TokenPayload
from integrations.azure_cosmos_db import get_container, query_items, create_item, read_item, delete_item, replace_item

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")



async def get_user_by_userid(user_id: str) -> Optional[UserInDB]:
    users_container = await get_container("users")

    query = "SELECT * FROM c WHERE c.id = @user_id"
    parameters = [ { "name": "@user_id", "value": user_id } ]  # FIXED KEY "name"

    items = users_container.query_items(
        query=query,
        parameters=parameters,
    )

    users = [item async for item in items]  # Async iterator

    if users:
        user_data = users[0]

        return UserInDB(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            password_hash=user_data["password_hash"],
            role=user_data["role"],
            created_at=datetime.fromisoformat(user_data["created_at"]) if isinstance(user_data["created_at"], str) else user_data["created_at"],
            active=user_data.get("active", True),
            last_login=datetime.fromisoformat(user_data["last_login"]) if user_data.get("last_login") else None,
            is_admin=user_data["is_admin"] if "is_admin" in user_data else False
        )
    return None








async def get_user_by_username(username: str) -> Optional[UserInDB]:
    """
    Get a user by username from Cosmos DB.
    
    Args:
        username: Username to look up
        
    Returns:
        Optional[UserInDB]: User if found, None otherwise
    """
    users_container = await get_container("users")
    query = "SELECT * FROM c WHERE c.username = @username"
    parameters = [{
        "name": "@username",
        "value": username
    }]
    users = await query_items("users", query, parameters)
    if users:
        user_data = users[0]
        return UserInDB(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            password_hash=user_data["password_hash"],
            role=user_data["role"],
            created_at=datetime.fromisoformat(user_data["created_at"]) if isinstance(user_data["created_at"], str) else user_data["created_at"],
            active=user_data.get("active", True),
            last_login=datetime.fromisoformat(user_data["last_login"]) if user_data.get("last_login") else None
        )
    return None


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if the password matches the hash, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


async def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """
    Authenticate a user with username and password.
    
    Args:
        username: Username
        password: Plain text password
        
    Returns:
        Optional[UserInDB]: User if authentication succeeds, None otherwise
    """
    user = await get_user_by_username(username)
    if not user:
        return None
    if not await verify_password(password, user.password_hash):
        return None
    
    # Update last_login field
    users_container = await get_container("users")
    user_item = json.loads(json.dumps({
    **user.dict(),
    "last_login": datetime.utcnow().isoformat()
        }, default=pydantic_encoder))
    await users_container.replace_item(item=user.id, body=user_item)
    
    return user


async def create_access_token(
    subject: str,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str, datetime]:
    """
    Create a JWT access token.
    
    Args:
        subject: Token subject (user ID)
        username: Username
        role: User role
        expires_delta: Token expiration time
        
    Returns:
        Tuple[str, str, datetime]: Token, JTI, and expiration time
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    jti = str(uuid.uuid4())
    
    to_encode = {
        "sub": subject,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": jti,
        "type": "access"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt, jti, expire


async def create_refresh_token(
    subject: str,
    username: str,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str, datetime]:
    """
    Create a JWT refresh token.
    
    Args:
        subject: Token subject (user ID)
        username: Username
        role: User role
        expires_delta: Token expiration time
        
    Returns:
        Tuple[str, str, datetime]: Token, JTI, and expiration time
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    
    jti = str(uuid.uuid4())
    
    to_encode = {
        "sub": subject,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": jti,
        "type": "refresh"
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt, jti, expire


async def create_tokens(user_id: str, username: str, role: str) -> TokenResponse:
    """
    Create access and refresh tokens for a user.
    
    Args:
        user_id: User ID
        username: Username
        role: User role
        
    Returns:
        TokenResponse: Access and refresh tokens
    """
    access_token, access_jti, access_expire = await create_access_token(
        subject=user_id,
        username=username,
        role=role
    )
    
    refresh_token, refresh_jti, refresh_expire = await create_refresh_token(
        subject=user_id,
        username=username,
        role=role
    )
    
    # Store the refresh token in Cosmos DB
    await create_item(settings.REFRESH_TOKEN_CONTAINER_NAME, {
        "id": refresh_jti,
        "user_id": user_id,
        "username": username,
        "expiration": refresh_expire.isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "type": "refresh"
    })
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int((access_expire - datetime.utcnow()).total_seconds())
    )

async def verify_token(token: str, token_type: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        print("Payload:", payload)

        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if token_type == "refresh":
            active_token = await read_item(settings.REFRESH_TOKEN_CONTAINER_NAME, payload.get("jti"), payload.get("jti"))
            if not active_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has been revoked or is invalid",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return TokenPayload(
            sub=payload.get("sub"),
            role=payload.get("role"),
            exp=payload.get("exp"),
            iat=payload.get("iat"),
            jti=payload.get("jti"),
            type=payload.get("type")
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def refresh_access_token(refresh_token: str) -> TokenResponse:
    """
    Refresh an access token using a refresh token.
    
    Args:
        refresh_token: Refresh token
        
    Returns:
        TokenResponse: New access and refresh tokens
        
    Raises:
        HTTPException: If the refresh token is invalid
    """
    # Verify the refresh token
    payload = await verify_token(refresh_token, "refresh")
    
    # Get the user
    user = await get_user_by_userid(payload.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Blacklist the old refresh token in Cosmos DB
    await delete_item(settings.REFRESH_TOKEN_CONTAINER_NAME, payload.jti, payload.jti)
    
    # Create new tokens
    return await create_tokens(user.id, user.username, user.role)


async def create_user(
    username: str,
    email: str,
    password: str,
    role: str
) -> UserInDB:
    """
    Create a new user.
    
    Args:
        username: Username
        email: Email
        password: Plain text password
        role: User role
        
    Returns:
        UserInDB: Created user
        
    Raises:
        HTTPException: If user creation fails
    """
    user_id = str(uuid.uuid4())
    password_hash = await get_password_hash(password)
    
    # Create a new user in Cosmos DB
    users_container = await get_container("users")
    user_item = {
        "id": user_id,
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "created_at": datetime.utcnow().isoformat(),
        "active": True,
        "last_login": None
    }
    await create_item("users", user_item)
    
    return UserInDB(
        id=user_id,
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        created_at=datetime.utcnow(),
        active=True
    )




