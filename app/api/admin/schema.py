"""
Admin API schemas for FastAPI Azure Backend.

This module defines Pydantic models for admin-related requests and responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator
from datetime import datetime
from enum import Enum

from api.auth.schema import UserRole


class UserCreate(BaseModel):
    """User creation model."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=8, description="Password")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    is_admin: bool = Field(default=False, description="Admin flag")
    permissions: Optional[List[str]] = Field(default=None, description="User permissions")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "john.doe@example.com",
                "password": "StrongP@ssw0rd",
                "role": "user",
                "is_admin": False,
                "permissions": ["read:files", "write:files"]
            }
        }


class UserUpdate(BaseModel):
    """User update model."""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username")
    email: Optional[EmailStr] = Field(None, description="Email address")
    password: Optional[str] = Field(None, min_length=8, description="Password")
    role: Optional[UserRole] = Field(None, description="User role")
    is_admin: Optional[bool] = Field(None, description="Admin flag")
    permissions: Optional[List[str]] = Field(None, description="User permissions")
    active: Optional[bool] = Field(None, description="User active status")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "john.doe@example.com",
                "role": "admin",
                "is_admin": True,
                "permissions": ["read:files", "write:files", "admin:users"],
                "active": True
            }
        }


class UserResponse(BaseModel):
    """User response model."""
    id: str = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: UserRole = Field(..., description="User role")
    is_admin: bool = Field(False, description="Admin flag")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    active: bool = Field(..., description="User active status")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "johndoe",
                "email": "john.doe@example.com",
                "role": "admin",
                "is_admin": True,
                "permissions": ["read:files", "write:files", "admin:users"],
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-02T00:00:00Z",
                "last_login": "2025-01-03T00:00:00Z",
                "active": True
            }
        }


class UserListResponse(BaseModel):
    """User list response model."""
    items: List[UserResponse] = Field(..., description="Users")
    total: int = Field(..., description="Total number of users")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")


class RoleCreate(BaseModel):
    """Role creation model."""
    name: str = Field(..., min_length=3, max_length=50, description="Role name")
    description: str = Field(..., description="Role description")
    permissions: List[str] = Field(..., description="Role permissions")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "content_editor",
                "description": "Can edit and manage content",
                "permissions": ["read:files", "write:files", "read:tasks", "write:tasks"]
            }
        }


class RoleUpdate(BaseModel):
    """Role update model."""
    name: Optional[str] = Field(None, min_length=3, max_length=50, description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    permissions: Optional[List[str]] = Field(None, description="Role permissions")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "content_editor",
                "description": "Can edit and manage all content",
                "permissions": ["read:files", "write:files", "read:tasks", "write:tasks", "delete:tasks"]
            }
        }


class RoleResponse(BaseModel):
    """Role response model."""
    id: str = Field(..., description="Role ID")
    name: str = Field(..., description="Role name")
    description: str = Field(..., description="Role description")
    permissions: List[str] = Field(..., description="Role permissions")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    created_by: str = Field(..., description="Creator user ID")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "content_editor",
                "description": "Can edit and manage all content",
                "permissions": ["read:files", "write:files", "read:tasks", "write:tasks", "delete:tasks"],
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-02T00:00:00Z",
                "created_by": "550e8400-e29b-41d4-a716-446655440001"
            }
        }


class RoleListResponse(BaseModel):
    """Role list response model."""
    items: List[RoleResponse] = Field(..., description="Roles")
    total: int = Field(..., description="Total number of roles")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")



class MappingCreate(BaseModel):
    """Mapping creation model."""
    role_id: str = Field(..., description="Role ID")
    task_id: str = Field(..., description="Task ID")
    prompt_id: str = Field(..., description="Prompt ID")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Mapping parameters")
    is_default: bool = Field(default=False, description="Whether this is the default mapping")
    
    class Config:
        schema_extra = {
            "example": {
                "role_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_id": "550e8400-e29b-41d4-a716-446655440001",
                "prompt_id": "550e8400-e29b-41d4-a716-446655440002",
                "parameters": {
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                "is_default": True
            }
        }


class MappingUpdate(BaseModel):
    """Mapping update model."""
    role_id: Optional[str] = Field(None, description="Role ID")
    task_id: Optional[str] = Field(None, description="Task ID")
    prompt_id: Optional[str] = Field(None, description="Prompt ID")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Mapping parameters")
    is_default: Optional[bool] = Field(None, description="Whether this is the default mapping")
    
    class Config:
        schema_extra = {
            "example": {
                "parameters": {
                    "temperature": 0.5,
                    "max_tokens": 2000
                },
                "is_default": True
            }
        }


class MappingResponse(BaseModel):
    """Mapping response model."""
    id: str = Field(..., description="Mapping ID")
    role_id: str = Field(..., description="Role ID")
    task_id: str = Field(..., description="Task ID")
    prompt_id: str = Field(..., description="Prompt ID")
    parameters: Dict[str, Any] = Field(..., description="Mapping parameters")
    is_default: bool = Field(..., description="Whether this is the default mapping")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    created_by: str = Field(..., description="Creator user ID")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "role_id": "550e8400-e29b-41d4-a716-446655440001",
                "task_id": "550e8400-e29b-41d4-a716-446655440002",
                "prompt_id": "550e8400-e29b-41d4-a716-446655440003",
                "parameters": {
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                "is_default": True,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-02T00:00:00Z",
                "created_by": "550e8400-e29b-41d4-a716-446655440004"
            }
        }


class MappingListResponse(BaseModel):
    """Mapping list response model."""
    items: List[MappingResponse] = Field(..., description="Mappings")
    total: int = Field(..., description="Total number of mappings")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")


class RoleAssignment(BaseModel):
    """Role assignment model."""
    role_id: str = Field(..., description="Role ID")
    
    class Config:
        schema_extra = {
            "example": {
                "role_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class UserActivationUpdate(BaseModel):
    """User activation update model."""
    active: bool = Field(..., description="User active status")
    
    class Config:
        schema_extra = {
            "example": {
                "active": True
            }
        }
