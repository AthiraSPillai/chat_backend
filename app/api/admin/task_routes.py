from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.admin.task_schema import TaskCreate, TaskUpdate, TaskInDB
from services.task_management import create_task, get_task_by_id, get_all_tasks, update_task, delete_task
from api.auth.dependency import get_current_active_user
from utils.response import SuccessResponse

router = APIRouter()

@router.post("/tasks", response_model=TaskInDB, status_code=status.HTTP_201_CREATED)
async def create_new_task(
    task_data: TaskCreate,
    current_user: dict = Depends(get_current_active_user)
) -> TaskInDB:
    # Add admin check here if needed
    task = await create_task(task_data)
    return task

@router.get("/tasks/{task_id}", response_model=TaskInDB)
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_active_user)
) -> TaskInDB:
    task = await get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task

@router.get("/tasks", response_model=List[TaskInDB])
async def list_tasks(
    current_user: dict = Depends(get_current_active_user)
) -> List[TaskInDB]:
    tasks = await get_all_tasks()
    return tasks

@router.put("/tasks/{task_id}", response_model=TaskInDB)
async def update_existing_task(
    task_id: str,
    task_data: TaskUpdate,
    current_user: dict = Depends(get_current_active_user)
) -> TaskInDB:
    task = await update_task(task_id, task_data)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task

@router.delete("/tasks/{task_id}", response_model=SuccessResponse)
async def delete_existing_task(
    task_id: str,
    current_user: dict = Depends(get_current_active_user)
) -> SuccessResponse:
    success = await delete_task(task_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return SuccessResponse(message="Task deleted successfully")


