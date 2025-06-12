"""
Admin API schemas for FastAPI Azure Backend.

This module defines Pydantic models for admin-related requests and responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class PromptCreate(BaseModel):
    """Prompt creation model."""
    name: str = Field(..., min_length=3, max_length=100, description="Prompt name")
    description: str = Field(..., description="Prompt description")
    content: str = Field(..., description="Prompt content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Prompt metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "translation_prompt",
                "description": "System prompt for translation tasks",
                "content": "You are a helpful translation assistant. Translate the following text from {source_language} to {target_language}:\n\n{text}",
                "metadata": {
                    "language": "en",
                    "tags": ["translation", "multilingual"],
                    "parameters": ["source_language", "target_language", "text"]
                }
            }
        }


class PromptUpdate(BaseModel):
    """Prompt update model."""
    name: Optional[str] = Field(None, min_length=3, max_length=100, description="Prompt name")
    description: Optional[str] = Field(None, description="Prompt description")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Prompt metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "enhanced_translation_prompt",
                "description": "Enhanced system prompt for translation tasks with formatting preservation",
                "metadata": {
                    "language": "en",
                    "tags": ["translation", "multilingual", "formatting"],
                    "parameters": ["source_language", "target_language", "text", "preserve_formatting"]
                }
            }
        }


class PromptContentUpdate(BaseModel):
    """Prompt content update model."""
    content: str = Field(..., description="Prompt content")
    create_new_version: bool = Field(default=True, description="Whether to create a new version")
    
    class Config:
        schema_extra = {
            "example": {
                "content": "You are a helpful translation assistant. Translate the following text from {source_language} to {target_language} while preserving the original formatting:\n\n{text}\n\nIf {preserve_formatting} is true, maintain all paragraph breaks and formatting.",
                "create_new_version": True
            }
        }


class PromptResponse(BaseModel):
    """Prompt response model."""
    id: str = Field(..., description="Prompt ID")
    name: str = Field(..., description="Prompt name")
    description: str = Field(..., description="Prompt description")
    version: int = Field(..., description="Prompt version")
    blob_path: str = Field(..., description="Blob path")
    content_preview: str = Field(..., description="Content preview")
    metadata: Dict[str, Any] = Field(..., description="Prompt metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Update timestamp")
    created_by: str = Field(..., description="Creator user ID")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "translation_prompt",
                "description": "System prompt for translation tasks",
                "version": 2,
                "blob_path": "prompts/550e8400-e29b-41d4-a716-446655440000/v2.txt",
                "content_preview": "You are a helpful translation assistant. Translate the following text...",
                "metadata": {
                    "language": "en",
                    "tags": ["translation", "multilingual"],
                    "parameters": ["source_language", "target_language", "text"]
                },
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-02T00:00:00Z",
                "created_by": "550e8400-e29b-41d4-a716-446655440001"
            }
        }


class PromptListResponse(BaseModel):
    """Prompt list response model."""
    items: List[PromptResponse] = Field(..., description="Prompts")
    total: int = Field(..., description="Total number of prompts")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")


class PromptContentResponse(BaseModel):
    """Prompt content response model."""
    id: str = Field(..., description="Prompt ID")
    name: str = Field(..., description="Prompt name")
    version: int = Field(..., description="Prompt version")
    content: str = Field(..., description="Prompt content")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "translation_prompt",
                "version": 2,
                "content": "You are a helpful translation assistant. Translate the following text from {source_language} to {target_language}:\n\n{text}"
            }
        }

