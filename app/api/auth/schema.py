from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


class TokenPayload(BaseModel):
    """JWT token payload model."""
    sub: str = Field(..., description="Subject (user ID)")
    role: str = Field(..., description="User role")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    jti: str = Field(..., description="JWT ID")
    type: str = Field(..., description="Token type (access or refresh)")
    session_id: Optional[str] = None  # Optional session ID for tracking user sessions


class TokenResponse(BaseModel):
    """Token response model."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")


class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "user",
                "password": "password"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str = Field(..., description="JWT refresh token")


class UserBase(BaseModel):
    """Base user model."""
    username: str = Field(..., description="Username")
    email: EmailStr = Field(..., description="Email address")
    role: UserRole = Field(..., description="User role")


class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(..., description="Password")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "securepassword",
                "role": "user"
            }
        }


class UserUpdate(BaseModel):
    """User update model."""
    email: Optional[EmailStr] = Field(None, description="Email address")
    password: Optional[str] = Field(None, description="Password")
    role: Optional[UserRole] = Field(None, description="User role")


class UserResponse(UserBase):
    """User response model."""
    id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "user123",
                "username": "user",
                "email": "user@example.com",
                "role": "user",
                "created_at": "2025-06-08T12:00:00Z",
                "updated_at": "2025-06-08T14:30:00Z"
            }
        }


class UserInDB(UserBase):
    """User model as stored in the database."""
    id: str = Field(..., description="User ID")
    password_hash: str = Field(..., description="Hashed password")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    active: bool = Field(default=True, description="Whether the user is active")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    is_admin: bool = Field(default=False, description="Whether the user is an admin")
    permissions: List[str] = Field(default_factory=list, description="List of user permissions")


class TokenBlacklist(BaseModel):
    """Token blacklist model."""
    jti: str = Field(..., description="JWT ID")
    expiration: datetime = Field(..., description="Token expiration timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")



class CurrentUser(UserInDB):
    session_id: Optional[str]   # extracted from JWT token