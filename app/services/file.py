"""
File service for FastAPI Azure Backend.

This module provides functions for managing files in Azure Blob Storage.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple, BinaryIO
from dataclasses import dataclass

from integrations.azure_cosmos_db import create_item, read_item, replace_item, delete_item, query_items_with_pagination
from integrations.azure_blob import (
    upload_blob, download_blob, delete_blob, 
    generate_sas_url, get_blob_properties
)
from api.files.schema import FileVisibility, FileMetadata
from config import settings
logger = logging.getLogger(__name__)


@dataclass
class UploadUrl:
    """Upload URL data class."""
    url: str
    expires_at: datetime


@dataclass
class DownloadUrl:
    """Download URL data class."""
    url: str
    expires_at: datetime


async def create_file(
    user_id: str,
    filename: str,
    description: Optional[str] = None,
    visibility: FileVisibility = FileVisibility.PRIVATE,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Create a new file entry.
    
    Args:
        user_id: User ID
        filename: File name
        description: File description
        visibility: File visibility
        tags: File tags
        
    Returns:
        Dict[str, Any]: Created file entry
    """
    file_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Determine container based on visibility
    container = "user-files" if visibility == FileVisibility.PRIVATE else "shared-files"
    
    # Create blob path
    blob_path = f"{user_id}/{file_id}/{filename}" if visibility == FileVisibility.PRIVATE else f"shared/{file_id}/{filename}"
    
    # Create file entry
    file_entry = {
        "id": file_id,
        "user_id": user_id,
        "filename": filename,
        "description": description,
        "visibility": visibility,
        "blob_path": blob_path,
        "container": container,
        "tags": tags or [],
        "metadata": {
            "content_type": "",  # Will be updated after upload
            "size_bytes": 0,     # Will be updated after upload
            "original_filename": filename,
            "extension": filename.split(".")[-1] if "." in filename else "",
            "file_type": "OTHER",  # Will be updated after upload
            "created_at": now.isoformat(),
            "is_processed": False
        },
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Save to database
    result = await create_item("files", file_entry)
    
    return result


async def update_file(
    file_id: str,
    user_id: str,
    filename: Optional[str] = None,
    description: Optional[str] = None,
    visibility: Optional[FileVisibility] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Update a file entry.
    
    Args:
        file_id: File ID
        user_id: User ID
        filename: New file name
        description: New file description
        visibility: New file visibility
        tags: New file tags
        
    Returns:
        Dict[str, Any]: Updated file entry
    """
    # Get existing file
    file = await get_file_by_id(file_id)
    if not file:
        raise ValueError(f"File {file_id} not found")
    
    # Check ownership
    if file["user_id"] != user_id:
        raise ValueError(f"User {user_id} does not own file {file_id}")
    
    # Update fields
    if filename is not None:
        file["filename"] = filename
    
    if description is not None:
        file["description"] = description
    
    if visibility is not None and visibility != file["visibility"]:
        # Visibility change requires moving the blob
        old_container = file["container"]
        new_container = "user-files" if visibility == FileVisibility.PRIVATE else "shared-files"
        
        old_blob_path = file["blob_path"]
        new_blob_path = f"{user_id}/{file_id}/{file['filename']}" if visibility == FileVisibility.PRIVATE else f"shared/{file_id}/{file['filename']}"
        
        # Move blob (download and re-upload)
        content, content_type, _ = await download_blob(old_container, old_blob_path)
        await upload_blob(new_container, new_blob_path, content, content_type)
        await delete_blob(old_container, old_blob_path)
        
        # Update file entry
        file["visibility"] = visibility
        file["container"] = new_container
        file["blob_path"] = new_blob_path
    
    if tags is not None:
        file["tags"] = tags
    
    # Update timestamp
    file["updated_at"] = datetime.utcnow().isoformat()
    
    # Save to database
    result = await replace_item("files", file_id, file)
    
    return result


async def delete_file(file_id: str, user_id: str) -> None:
    """
    Delete a file.
    
    Args:
        file_id: File ID
        user_id: User ID
    """
    # Get existing file
    file = await get_file_by_id(file_id)
    if not file:
        raise ValueError(f"File {file_id} not found")
    
    # Check ownership
    if file["user_id"] != user_id:
        raise ValueError(f"User {user_id} does not own file {file_id}")
    
    # Delete blob
    await delete_blob(file["container"], file["blob_path"])
    
    # Delete file entry
    await delete_item("files", file_id, file_id)


async def get_file_by_id(file_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a file by ID.
    
    Args:
        file_id: File ID
        
    Returns:
        Optional[Dict[str, Any]]: File if found, None otherwise
    """
    return await read_item("files", file_id, file_id)


async def check_file_access(file: Dict[str, Any], user_id: str) -> bool:
    """
    Check if a user has access to a file.
    
    Args:
        file: File entry
        user_id: User ID
        
    Returns:
        bool: True if the user has access, False otherwise
    """
    # User owns the file
    if file["user_id"] == user_id:
        return True
    
    # File is shared
    if file["visibility"] == FileVisibility.SHARED:
        return True
    
    return False


async def get_user_files(
    user_id: str,
    visibility: Optional[FileVisibility] = None,
    tags: Optional[List[str]] = None,
    file_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get files owned by a user.
    
    Args:
        user_id: User ID
        visibility: Optional visibility filter
        tags: Optional tags filter
        file_type: Optional file type filter
        page: Page number
        page_size: Page size
        
    Returns:
        Tuple[List[Dict[str, Any]], int]: Files and total count
    """
    # Build query
    query = "SELECT * FROM c WHERE c.user_id = @user_id"
    parameters = [{"name": "@user_id", "value": user_id}]
    
    if visibility:
        query += " AND c.visibility = @visibility"
        parameters.append({"name": "@visibility", "value": visibility})
    
    if tags:
        # Filter by any of the specified tags
        tag_conditions = []
        for i, tag in enumerate(tags):
            tag_param = f"@tag{i}"
            tag_conditions.append(f"ARRAY_CONTAINS(c.tags, {tag_param})")
            parameters.append({"name": tag_param, "value": tag})
        
        query += f" AND ({' OR '.join(tag_conditions)})"
    
    if file_type:
        query += " AND c.metadata.file_type = @file_type"
        parameters.append({"name": "@file_type", "value": file_type})
    
    query += " ORDER BY c.created_at DESC"
    
    # Execute query
    return await query_items_with_pagination(
       settings.FILES_CONTAINER_NAME,
        query,
        parameters,
        page,
        page_size
    )


async def get_shared_files(
    tags: Optional[List[str]] = None,
    file_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get shared files.
    
    Args:
        tags: Optional tags filter
        file_type: Optional file type filter
        page: Page number
        page_size: Page size
        
    Returns:
        Tuple[List[Dict[str, Any]], int]: Files and total count
    """
    # Build query
    query = "SELECT * FROM c WHERE c.visibility = 'shared'"
    parameters = []
    
    if tags:
        # Filter by any of the specified tags
        tag_conditions = []
        for i, tag in enumerate(tags):
            tag_param = f"@tag{i}"
            tag_conditions.append(f"ARRAY_CONTAINS(c.tags, {tag_param})")
            parameters.append({"name": tag_param, "value": tag})
        
        query += f" AND ({' OR '.join(tag_conditions)})"
    
    if file_type:
        query += " AND c.metadata.file_type = @file_type"
        parameters.append({"name": "@file_type", "value": file_type})
    
    query += " ORDER BY c.created_at DESC"
    
    # Execute query
    return await query_items_with_pagination(
        settings.FILES_CONTAINER_NAME,
        query,
        parameters,
        page,
        page_size
    )


async def generate_upload_url(file_id: str, blob_path: str) -> UploadUrl:
    """
    Generate a URL for uploading a file.
    
    Args:
        file_id: File ID
        blob_path: Blob path
        
    Returns:
        UploadUrl: Upload URL and expiration
    """
    # Determine container from blob path
    container = "user-files" if not blob_path.startswith("shared/") else "shared-files"
    
    # Generate SAS URL with write permission
    url, expiry = await generate_sas_url(container, blob_path, "w")
    
    return UploadUrl(url=url, expires_at=expiry)


async def get_file_download_url(file_id: str, blob_path: str) -> DownloadUrl:
    """
    Generate a URL for downloading a file.
    
    Args:
        file_id: File ID
        blob_path: Blob path
        
    Returns:
        DownloadUrl: Download URL and expiration
    """
    # Determine container from blob path
    container = "user-files" if not blob_path.startswith("shared/") else "shared-files"
    
    # Generate SAS URL with read permission
    url, expiry = await generate_sas_url(container, blob_path, "r")
    
    return DownloadUrl(url=url, expires_at=expiry)


async def get_file_content(file_id: str, blob_path: str) -> Tuple[BinaryIO, str, int]:
    """
    Get file content.
    
    Args:
        file_id: File ID
        blob_path: Blob path
        
    Returns:
        Tuple[BinaryIO, str, int]: Content stream, content type, and content length
    """
    # Determine container from blob path
    container = "user-files" if not blob_path.startswith("shared/") else "shared-files"
    
    # Download blob
    content, content_type, content_length = await download_blob(container, blob_path)
    
    return content, content_type, content_length


async def update_file_metadata_after_upload(file_id: str) -> Dict[str, Any]:
    """
    Update file metadata after upload.
    
    Args:
        file_id: File ID
        
    Returns:
        Dict[str, Any]: Updated file entry
    """
    # Get existing file
    file = await get_file_by_id(file_id)
    if not file:
        raise ValueError(f"File {file_id} not found")
    
    # Get blob properties
    properties = await get_blob_properties(file["container"], file["blob_path"])
    
    # Update metadata
    file["metadata"]["content_type"] = properties.content_settings.content_type
    file["metadata"]["size_bytes"] = properties.size
    
    # Determine file type based on content type
    content_type = properties.content_settings.content_type.lower()
    if content_type.startswith("image/"):
        file["metadata"]["file_type"] = "IMAGE"
    elif content_type.startswith("video/"):
        file["metadata"]["file_type"] = "VIDEO"
    elif content_type.startswith("audio/"):
        file["metadata"]["file_type"] = "AUDIO"
    elif content_type in ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
        file["metadata"]["file_type"] = "DOCUMENT"
    else:
        file["metadata"]["file_type"] = "OTHER"
    
    # Update timestamp
    file["updated_at"] = datetime.utcnow().isoformat()
    
    # Save to database
    result = await replace_item("files", file_id, file)
    
    return result


@dataclass
class ProcessingJob:
    """Processing job data class."""
    id: str
    status: str
    estimated_completion: Optional[datetime] = None


async def process_file(
    file_id: str,
    user_id: str,
    processing_type: str,
    options: Dict[str, Any]
) -> ProcessingJob:
    """
    Start processing a file.
    
    Args:
        file_id: File ID
        user_id: User ID
        processing_type: Processing type
        options: Processing options
        
    Returns:
        ProcessingJob: Processing job details
    """
    # Get existing file
    file = await get_file_by_id(file_id)
    if not file:
        raise ValueError(f"File {file_id} not found")
    
    # Check ownership
    if file["user_id"] != user_id:
        raise ValueError(f"User {user_id} does not own file {file_id}")
    
    # Create processing job
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    estimated_completion = now + timedelta(minutes=5)  # Estimate 5 minutes for processing
    
    # In a real implementation, this would create a background job
    # For this example, we just update the file metadata
    file["metadata"]["is_processed"] = True
    file["metadata"]["processing_status"] = "completed"
    file["metadata"]["last_processed"] = now.isoformat()
    file["updated_at"] = now.isoformat()
    
    # Save to database
    await replace_item("files", file_id, file)
    
    return ProcessingJob(
        id=job_id,
        status="pending",
        estimated_completion=estimated_completion
    )
