"""
Authentication service for FastAPI Azure Backend with multi-session tracking.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from pydantic.json import pydantic_encoder

import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Request

from config import settings
from api.auth.schema import CurrentUser, UserInDB, TokenResponse, TokenPayload
from integrations.azure_cosmos_db import (
    get_container,
    query_items,
    create_item,
    read_item,
    delete_item,
    replace_item
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_user_by_userid(user_id: str) -> Optional[UserInDB]:
    users_container = await get_container("users")
    query = "SELECT * FROM c WHERE c.id = @user_id"
    parameters = [{"name": "@user_id", "value": user_id}]
    items = users_container.query_items(query=query, parameters=parameters)
    users = [item async for item in items]
    if users:
        user_data = users[0]
        return UserInDB(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            password_hash=user_data["password_hash"],
            role=user_data["role"],
            created_at=datetime.fromisoformat(user_data["created_at"])
            if isinstance(user_data["created_at"], str)
            else user_data["created_at"],
            active=user_data.get("active", True),
            last_login=datetime.fromisoformat(user_data["last_login"])
            if user_data.get("last_login")
            else None,
            is_admin=user_data.get("is_admin", False)
        )
    return None


async def get_user_by_username(username: str) -> Optional[UserInDB]:
    query = "SELECT * FROM c WHERE c.username = @username"
    parameters = [{"name": "@username", "value": username}]
    users = await query_items( settings.USERS_CONTAINER_NAME, query, parameters)
    if users:
        user_data = users[0]
        return UserInDB(
            id=user_data["id"],
            username=user_data["username"],
            email=user_data["email"],
            password_hash=user_data["password_hash"],
            role=user_data["role"],
            created_at=datetime.fromisoformat(user_data["created_at"])
            if isinstance(user_data["created_at"], str)
            else user_data["created_at"],
            active=user_data.get("active", True),
            last_login=datetime.fromisoformat(user_data["last_login"])
            if user_data.get("last_login")
            else None
        )
    return None


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = await get_user_by_username(username)
    if not user:
        return None
    if not await verify_password(password, user.password_hash):
        return None
    users_container = await get_container("users")
    user_item = json.loads(json.dumps({
        **user.dict(),
        "last_login": datetime.utcnow().isoformat()
    }, default=pydantic_encoder))
    await users_container.replace_item(item=user.id, body=user_item)
    return user


async def create_access_token(subject: str, username: str, role: str, session_id: str, expires_delta: Optional[timedelta] = None) -> Tuple[str, str, datetime]:
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES))
    jti = str(uuid.uuid4())
    payload = {
        "sub": subject,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": jti,
        "sid": session_id,
        "type": "access",
        "session_id": session_id
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expire


async def create_refresh_token(subject: str, username: str, role: str, session_id: str, expires_delta: Optional[timedelta] = None) -> Tuple[str, str, datetime]:
    expire = datetime.utcnow() + (expires_delta or timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS))
    jti = str(uuid.uuid4())
    payload = {
        "sub": subject,
        "username": username,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": jti,
        "sid": session_id,
        "type": "refresh",
        "session_id": session_id

    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expire


async def create_tokens(user_id: str, username: str, role: str) -> TokenResponse:
    
    session_id = str(uuid.uuid4())
    access_token, access_jti, access_expire = await create_access_token(user_id, username, role, session_id)
    refresh_token, refresh_jti, refresh_expire = await create_refresh_token(user_id, username, role, session_id)
    await create_item(settings.SESSION_CONTAINER_NAME, {
        "id": session_id,
        "user_id": user_id,
        "username": username,
        "access_jti": access_jti,
        "refresh_jti": refresh_jti,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": refresh_expire.isoformat(),
        "active": True
    })


    await create_item(settings.REFRESH_TOKEN_CONTAINER_NAME, {
        "id": refresh_jti,
        "user_id": user_id,
        "username": username,
        "expiration": refresh_expire.isoformat(),
        "created_at": datetime.utcnow().isoformat(),
        "session_id": session_id,
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
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        print(f"Decoded payload: {payload}")  # Debugging line
        if payload.get("type") != token_type:
            raise HTTPException(status_code=401, detail="Invalid token type.")

        if token_type == "refresh":
            jti = payload.get("jti")
            token_doc = await read_item(settings.REFRESH_TOKEN_CONTAINER_NAME, jti, jti)
            if not token_doc:
                raise HTTPException(status_code=401, detail="Refresh token invalid or revoked")

        return TokenPayload(
            sub=payload.get("sub"),
            role=payload.get("role"),
            exp=payload.get("exp"),
            iat=payload.get("iat"),
            jti=payload.get("jti"),
            type=payload.get("type"),
            sid=payload.get("session_id")
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token validation failed")


async def refresh_access_token(refresh_token: str) -> TokenResponse:
    payload = await verify_token(refresh_token, "refresh")
    user = await get_user_by_userid(payload.sub)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    await delete_item(settings.REFRESH_TOKEN_CONTAINER_NAME, payload.jti, payload.jti)
    return await create_tokens(user.id, user.username, user.role)


async def create_user(username: str, email: str, password: str, role: str) -> UserInDB:
    user_id = str(uuid.uuid4())
    password_hash = await get_password_hash(password)
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
