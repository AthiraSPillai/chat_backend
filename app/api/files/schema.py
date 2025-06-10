"""
File Library API schemas for FastAPI Azure Backend.

This module defines Pydantic models for file-related requests and responses.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class FileType(str, Enum):
    """File type enumeration."""
    DOCUMENT = "document"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    OTHER = "other"


class FileVisibility(str, Enum):
    """File visibility enumeration."""
    PRIVATE = "private"
    SHARED = "shared"


class FileMetadata(BaseModel):
    """File metadata model."""
    content_type: str = Field(..., description="File MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    original_filename: str = Field(..., description="Original filename")
    extension: str = Field(..., description="File extension")
    file_type: FileType = Field(..., description="File type category")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    last_accessed: Optional[datetime] = Field(None, description="Last access timestamp")
    is_processed: bool = Field(default=False, description="Whether file has been processed")
    processing_status: Optional[str] = Field(None, description="Processing status")
    processing_error: Optional[str] = Field(None, description="Processing error message")
    extracted_text_length: Optional[int] = Field(None, description="Length of extracted text")
    page_count: Optional[int] = Field(None, description="Number of pages (for documents)")
    custom_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")
    tags: List[str] = Field(default_factory=list, description="File tags")


class FileBase(BaseModel):
    """Base file model."""
    filename: str = Field(..., description="File name")
    description: Optional[str] = Field(None, description="File description")
    visibility: FileVisibility = Field(default=FileVisibility.PRIVATE, description="File visibility")
    tags: List[str] = Field(default_factory=list, description="File tags")


class FileCreate(FileBase):
    """File creation model."""
    # No additional fields needed, file content is uploaded separately
    pass
    
    class Config:
        schema_extra = {
            "example": {
                "filename": "document.pdf",
                "description": "Important document",
                "visibility": "private",
                "tags": ["report", "finance"]
            }
        }


class FileUpdate(BaseModel):
    """File update model."""
    filename: Optional[str] = Field(None, description="File name")
    description: Optional[str] = Field(None, description="File description")
    visibility: Optional[FileVisibility] = Field(None, description="File visibility")
    tags: Optional[List[str]] = Field(None, description="File tags")


class FileResponse(FileBase):
    """File response model."""
    id: str = Field(..., description="File ID")
    user_id: str = Field(..., description="Owner user ID")
    blob_path: str = Field(..., description="Blob storage path")
    url: str = Field(..., description="File URL")
    metadata: FileMetadata = Field(..., description="File metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "file123",
                "user_id": "user456",
                "filename": "document.pdf",
                "description": "Important document",
                "visibility": "private",
                "blob_path": "user-files/user456/file123.pdf",
                "url": "https://storage.azure.com/user-files/user456/file123.pdf",
                "tags": ["report", "finance"],
                "metadata": {
                    "content_type": "application/pdf",
                    "size_bytes": 1024000,
                    "original_filename": "original_document.pdf",
                    "extension": "pdf",
                    "file_type": "document",
                    "created_at": "2025-06-08T12:00:00Z",
                    "is_processed": True,
                    "page_count": 10
                },
                "created_at": "2025-06-08T12:00:00Z",
                "updated_at": "2025-06-08T14:30:00Z"
            }
        }


class FileInDB(FileResponse):
    """File model as stored in the database."""
    pass


class FileUploadResponse(BaseModel):
    """File upload response model."""
    file_id: str = Field(..., description="File ID")
    upload_url: str = Field(..., description="Upload URL for the file")
    expires_at: datetime = Field(..., description="URL expiration timestamp")


class FileListResponse(BaseModel):
    """File list response model."""
    items: List[FileResponse] = Field(..., description="List of files")
    total: int = Field(..., description="Total number of files")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")


class FileProcessingRequest(BaseModel):
    """File processing request model."""
    file_id: str = Field(..., description="File ID to process")
    processing_type: str = Field(..., description="Type of processing to perform")
    options: Dict[str, Any] = Field(default_factory=dict, description="Processing options")
    
    class Config:
        schema_extra = {
            "example": {
                "file_id": "file123",
                "processing_type": "extract_text",
                "options": {
                    "language": "en",
                    "extract_tables": True
                }
            }
        }


class FileProcessingResponse(BaseModel):
    """File processing response model."""
    file_id: str = Field(..., description="File ID")
    processing_id: str = Field(..., description="Processing job ID")
    status: str = Field(..., description="Processing status")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
