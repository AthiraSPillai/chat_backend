"""
Tasks API routes for FastAPI Azure Backend.

This module defines routes for task-related operations.
"""

from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from api.auth.dependency import get_current_active_user
from api.tasks.schema import (
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse,
    TaskResult, TaskStatusUpdate, TaskType, TaskStatus
)
from api.tasks.dependency import (
    get_task_type_filter, get_task_status_filter,
    get_file_id_filter, get_pagination_params, get_user_task
)
from services.task import (
    create_task, update_task, cancel_task, delete_task,
    get_user_tasks, get_task_result
)
from utils.pagination import PaginationParams
from utils.response import SuccessResponse

router = APIRouter()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_new_task(
    task_create: TaskCreate,
    background_tasks: BackgroundTasks,
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> TaskResponse:
    """
    Create a new task.
    
    Args:
        task_create: Task creation data
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        
    Returns:
        TaskResponse: Created task
    """
    # Create task in database
    task = await create_task(
        user_id=current_user.id,
        name=task_create.name,
        description=task_create.description,
        task_type=task_create.task_type,
        file_ids=task_create.file_ids,
        options=task_create.options,
        background_tasks=background_tasks
    )
    
    return TaskResponse(**task)


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    current_user: Annotated[dict, Depends(get_current_active_user)],
    task_type: Annotated[Optional[TaskType], Depends(get_task_type_filter)] = None,
    status: Annotated[Optional[TaskStatus], Depends(get_task_status_filter)] = None,
    file_id: Annotated[Optional[str], Depends(get_file_id_filter)] = None,
    pagination: Annotated[PaginationParams, Depends(get_pagination_params)] = PaginationParams()
) -> TaskListResponse:
    """
    List tasks owned by the current user.
    
    Args:
        task_type: Optional task type filter
        status: Optional status filter
        file_id: Optional file ID filter
        pagination: Pagination parameters
        current_user: Current authenticated user
        
    Returns:
        TaskListResponse: Paginated list of tasks
    """
    tasks, total = await get_user_tasks(
        user_id=current_user.id,
        task_type=task_type,
        status=status,
        file_id=file_id,
        page=pagination.page,
        page_size=pagination.page_size
    )
    
    pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return TaskListResponse(
        items=tasks,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task: Annotated[dict, Depends(get_user_task)]
) -> TaskResponse:
    """
    Get task details by ID.
    
    Args:
        task: Task from dependency
        
    Returns:
        TaskResponse: Task details
    """
    return TaskResponse(**task)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task_details(
    task_update: TaskUpdate,
    task: Annotated[dict, Depends(get_user_task)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> TaskResponse:
    """
    Update task details.
    
    Args:
        task_update: Task update data
        task: Task from dependency
        current_user: Current authenticated user
        
    Returns:
        TaskResponse: Updated task details
    """
    # Only allow updates if task is pending
    if task["status"] != TaskStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update task that is not in pending status"
        )
    
    updated_task = await update_task(
        task_id=task["id"],
        user_id=current_user.id,
        name=task_update.name,
        description=task_update.description,
        options=task_update.options
    )
    
    return TaskResponse(**updated_task)


@router.delete("/{task_id}", response_model=SuccessResponse)
async def delete_user_task(
    task: Annotated[dict, Depends(get_user_task)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> SuccessResponse:
    """
    Delete a task.
    
    Args:
        task: Task from dependency
        current_user: Current authenticated user
        
    Returns:
        SuccessResponse: Success message
    """
    await delete_task(task["id"], current_user.id)
    
    return SuccessResponse(message="Task deleted successfully")


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_user_task(
    task: Annotated[dict, Depends(get_user_task)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> TaskResponse:
    """
    Cancel a running task.
    
    Args:
        task: Task from dependency
        current_user: Current authenticated user
        
    Returns:
        TaskResponse: Updated task
    """
    # Only allow cancellation if task is pending or processing
    if task["status"] not in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel task that is not pending or processing"
        )
    
    updated_task = await cancel_task(task["id"], current_user.id)
    
    return TaskResponse(**updated_task)


@router.get("/{task_id}/result", response_model=TaskResult)
async def get_task_results(
    task: Annotated[dict, Depends(get_user_task)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> TaskResult:
    """
    Get task results.
    
    Args:
        task: Task from dependency
        current_user: Current authenticated user
        
    Returns:
        TaskResult: Task results
    """
    # Only allow getting results if task is completed
    if task["status"] != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task results are only available for completed tasks"
        )
    
    result = await get_task_result(task["id"], current_user.id)
    
    return result


