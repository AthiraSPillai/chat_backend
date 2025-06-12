"""
File Library API routes for FastAPI Azure Backend.

This module defines routes for file-related operations.
"""

from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse

from api.auth.dependency import get_current_active_user, get_admin_user
from api.files.schema import (
    FileCreate, FileUpdate, FileResponse, FileListResponse, 
    FileUploadResponse, FileProcessingRequest, FileProcessingResponse,
    FileVisibility
)
from api.files.dependency import (
    get_file_visibility_filter, get_file_tags_filter, 
    get_file_type_filter, get_pagination_params, get_user_file
)
from services.file import (
    create_file, update_file, delete_file, get_user_files,
    get_shared_files, generate_upload_url, process_file,
    get_file_content, get_file_download_url
)
from utils.pagination import PaginationParams
from utils.response import SuccessResponse

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def create_new_file(
    file_create: FileCreate,
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> FileUploadResponse:
    """
    Create a new file entry and get an upload URL.
    
    Args:
        file_create: File creation data
        current_user: Current authenticated user
        
    Returns:
        FileUploadResponse: File ID and upload URL
    """
    # Create file entry in database
    file_data = await create_file(
        user_id=current_user.id,
        filename=file_create.filename,
        description=file_create.description,
        visibility=file_create.visibility,
        tags=file_create.tags
    )
    
    # Generate upload URL
    upload_url = await generate_upload_url(file_data.id, file_data.blob_path)
    
    return FileUploadResponse(
        file_id=file_data.id,
        upload_url=upload_url.url,
        expires_at=upload_url.expires_at
    )


@router.get("/my", response_model=FileListResponse)
async def list_my_files(
    current_user: Annotated[dict, Depends(get_current_active_user)],
    visibility: Annotated[Optional[FileVisibility], Depends(get_file_visibility_filter)] = None,
    tags: Annotated[Optional[List[str]], Depends(get_file_tags_filter)] = None,
    file_type: Annotated[Optional[str], Depends(get_file_type_filter)] = None,
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)] = PaginationParams()
) -> FileListResponse:
    """
    List files owned by the current user.
    
    Args:
        visibility: Optional visibility filter
        tags: Optional tags filter
        file_type: Optional file type filter
        pagination: Pagination parameters
        current_user: Current authenticated user
        
    Returns:
        FileListResponse: Paginated list of files
    """
    files, total = await get_user_files(
        user_id=current_user.id,
        visibility=visibility,
        tags=tags,
        file_type=file_type,
        page=pagination.page,
        page_size=pagination.page_size
    )
    
    pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return FileListResponse(
        items=files,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages
    )


@router.get("/shared", response_model=FileListResponse)
async def list_shared_files(
    current_user: Annotated[dict, Depends(get_current_active_user)],
    tags: Annotated[Optional[List[str]], Depends(get_file_tags_filter)] = None,
    file_type: Annotated[Optional[str], Depends(get_file_type_filter)] = None,
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)] = PaginationParams()
) -> FileListResponse:
    """
    List shared files accessible to the current user.
    
    Args:
        tags: Optional tags filter
        file_type: Optional file type filter
        pagination: Pagination parameters
        current_user: Current authenticated user
        
    Returns:
        FileListResponse: Paginated list of shared files
    """
    files, total = await get_shared_files(
        tags=tags,
        file_type=file_type,
        page=pagination.page,
        page_size=pagination.page_size
    )
    
    pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return FileListResponse(
        items=files,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages
    )


@router.get("/{file_id}", response_model=FileResponse)
async def get_file(
    file: Annotated[dict, Depends(get_user_file)]
) -> FileResponse:
    """
    Get file details by ID.
    
    Args:
        file: File from dependency
        
    Returns:
        FileResponse: File details
    """
    return FileResponse(**file)


@router.put("/{file_id}", response_model=FileResponse)
async def update_file_details(
    file_update: FileUpdate,
    file: Annotated[dict, Depends(get_user_file)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> FileResponse:
    """
    Update file details.
    
    Args:
        file_update: File update data
        file: File from dependency
        current_user: Current authenticated user
        
    Returns:
        FileResponse: Updated file details
    """
    updated_file = await update_file(
        file_id=file["id"],
        user_id=current_user.id,
        filename=file_update.filename,
        description=file_update.description,
        visibility=file_update.visibility,
        tags=file_update.tags
    )
    
    return FileResponse(**updated_file)


@router.delete("/{file_id}", response_model=SuccessResponse)
async def delete_user_file(
    file: Annotated[dict, Depends(get_user_file)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> SuccessResponse:
    """
    Delete a file.
    
    Args:
        file: File from dependency
        current_user: Current authenticated user
        
    Returns:
        SuccessResponse: Success message
    """
    await delete_file(file["id"], current_user.id)
    
    return SuccessResponse(message="File deleted successfully")


@router.get("/{file_id}/download")
async def download_file(
    file: Annotated[dict, Depends(get_user_file)]
) -> StreamingResponse:
    """
    Download a file.
    
    Args:
        file: File from dependency
        
    Returns:
        StreamingResponse: File content stream
    """
    content_stream, content_type, content_length = await get_file_content(file["id"], file["blob_path"])
    
    return StreamingResponse(
        content_stream,
        media_type=content_type,
        headers={
            "Content-Disposition": "attachment; filename=" + file["filename"],
            "Content-Length": str(content_length)
        }
    )


@router.get("/{file_id}/download-url", response_model=dict)
async def get_download_url(
    file: Annotated[dict, Depends(get_user_file)]
) -> dict:
    """
    Get a temporary download URL for a file.
    
    Args:
        file: File from dependency
        
    Returns:
        dict: Download URL and expiration
    """
    download_url = await get_file_download_url(file["id"], file["blob_path"])
    
    return {
        "download_url": download_url.url,
        "expires_at": download_url.expires_at
    }


@router.post("/{file_id}/process", response_model=FileProcessingResponse)
async def start_file_processing(
    processing_request: FileProcessingRequest,
    file: Annotated[dict, Depends(get_user_file)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> FileProcessingResponse:
    """
    Start processing a file.
    
    Args:
        processing_request: Processing request data
        file: File from dependency
        current_user: Current authenticated user
        
    Returns:
        FileProcessingResponse: Processing job details
    """
    processing_job = await process_file(
        file_id=file["id"],
        user_id=current_user.id,
        processing_type=processing_request.processing_type,
        options=processing_request.options
    )
    
    return FileProcessingResponse(
        file_id=file["id"],
        processing_id=processing_job.id,
        status=processing_job.status,
        estimated_completion=processing_job.estimated_completion
    )


