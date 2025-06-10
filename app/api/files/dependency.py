"""
File Library API dependencies for FastAPI Azure Backend.

This module provides dependency injection functions for file-related operations.
"""

from typing import Annotated, Optional, List
from fastapi import Depends, HTTPException, status, Query

from api.auth.dependency import get_current_active_user
from api.files.schema import FileVisibility
from services.file import get_file_by_id, check_file_access
from utils.pagination import PaginationParams


async def get_file_visibility_filter(
    visibility: Optional[FileVisibility] = Query(None, description="Filter by file visibility")
) -> Optional[FileVisibility]:
    """
    Dependency to get file visibility filter.
    
    Args:
        visibility: Optional visibility filter
        
    Returns:
        Optional[FileVisibility]: The visibility filter or None
    """
    return visibility


async def get_file_tags_filter(
    tags: Optional[List[str]] = Query(None, description="Filter by file tags")
) -> Optional[List[str]]:
    """
    Dependency to get file tags filter.
    
    Args:
        tags: Optional tags filter
        
    Returns:
        Optional[List[str]]: The tags filter or None
    """
    return tags


async def get_file_type_filter(
    file_type: Optional[str] = Query(None, description="Filter by file type")
) -> Optional[str]:
    """
    Dependency to get file type filter.
    
    Args:
        file_type: Optional file type filter
        
    Returns:
        Optional[str]: The file type filter or None
    """
    return file_type


async def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page")
) -> PaginationParams:
    """
    Dependency to get pagination parameters.
    
    Args:
        page: Page number
        page_size: Items per page
        
    Returns:
        PaginationParams: Pagination parameters
    """
    return PaginationParams(page=page, page_size=page_size)


async def get_user_file(
    file_id: str,
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> dict:
    """
    Dependency to get a file owned by the current user.
    
    Args:
        file_id: File ID
        current_user: Current authenticated user
        
    Returns:
        dict: The file if it exists and is owned by the user
        
    Raises:
        HTTPException: If the file doesn't exist or the user doesn't have access
    """
    file = await get_file_by_id(file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check if the user has access to the file
    has_access = await check_file_access(file, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this file"
        )
    
    return file
