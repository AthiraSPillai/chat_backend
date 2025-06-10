"""
Tasks API dependencies for FastAPI Azure Backend.

This module provides dependency injection functions for task-related operations.
"""

from typing import Annotated, Optional, List
from fastapi import Depends, HTTPException, status, Query

from api.auth.dependency import get_current_active_user
from api.tasks.schema import TaskType, TaskStatus
from services.task import get_task_by_id, check_task_access
from utils.pagination import PaginationParams


async def get_task_type_filter(
    task_type: Optional[TaskType] = Query(None, description="Filter by task type")
) -> Optional[TaskType]:
    """
    Dependency to get task type filter.
    
    Args:
        task_type: Optional task type filter
        
    Returns:
        Optional[TaskType]: The task type filter or None
    """
    return task_type


async def get_task_status_filter(
    status: Optional[TaskStatus] = Query(None, description="Filter by task status")
) -> Optional[TaskStatus]:
    """
    Dependency to get task status filter.
    
    Args:
        status: Optional status filter
        
    Returns:
        Optional[TaskStatus]: The status filter or None
    """
    return status


async def get_file_id_filter(
    file_id: Optional[str] = Query(None, description="Filter by file ID")
) -> Optional[str]:
    """
    Dependency to get file ID filter.
    
    Args:
        file_id: Optional file ID filter
        
    Returns:
        Optional[str]: The file ID filter or None
    """
    return file_id


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


async def get_user_task(
    task_id: str,
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> dict:
    """
    Dependency to get a task owned by the current user.
    
    Args:
        task_id: Task ID
        current_user: Current authenticated user
        
    Returns:
        dict: The task if it exists and is owned by the user
        
    Raises:
        HTTPException: If the task doesn't exist or the user doesn't have access
    """
    task = await get_task_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    # Check if the user has access to the task
    has_access = await check_task_access(task, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this task"
        )
    
    return task
