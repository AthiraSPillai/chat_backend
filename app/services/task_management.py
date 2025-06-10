from azure.cosmos.exceptions import CosmosResourceNotFoundError
from integrations.azure_cosmos_db import cosmos_db_service
from api.admin.task_schema import TaskCreate, TaskUpdate, TaskInDB
import uuid
from datetime import datetime
from typing import Optional, List

async def create_task(task_data: TaskCreate) -> TaskInDB:
    container = await cosmos_db_service.get_container("tasks")
    new_task = TaskInDB(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        **task_data.model_dump()
    )
    await container.create_item(body=new_task.model_dump())
    return new_task

async def get_task_by_id(task_id: str) -> Optional[TaskInDB]:
    container = await cosmos_db_service.get_container("tasks")
    try:
        task = await container.read_item(item=task_id, partition_key=task_id)
        return TaskInDB(**task)
    except CosmosResourceNotFoundError:
        return None

async def get_all_tasks() -> List[TaskInDB]:
    container = await cosmos_db_service.get_container("tasks")
    tasks = []
    async for item in container.query_items(
        query="SELECT * FROM c",
    ):
        tasks.append(TaskInDB(**item))
    return tasks

async def update_task(task_id: str, task_data: TaskUpdate) -> Optional[TaskInDB]:
    container = await cosmos_db_service.get_container("tasks")
    existing_task = await get_task_by_id(task_id)
    if not existing_task:
        return None
    
    updated_data = task_data.model_dump(exclude_unset=True)
    for key, value in updated_data.items():
        setattr(existing_task, key, value)
    existing_task.updated_at = datetime.utcnow().isoformat()
    
    await container.replace_item(item=existing_task.id, body=existing_task.model_dump())
    return existing_task

async def delete_task(task_id: str) -> bool:
    container = await cosmos_db_service.get_container("tasks")
    try:
        await container.delete_item(item=task_id, partition_key=task_id)
        return True
    except CosmosResourceNotFoundError:
        return False


