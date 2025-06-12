"""
Task service for FastAPI Azure Backend.

This module provides functions for managing tasks.
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from fastapi import BackgroundTasks

from integrations.azure_cosmos_db import create_item, read_item, replace_item, delete_item, query_items_with_pagination
from services.file import get_file_by_id, check_file_access
from integrations.azure_openai import generate_summary, generate_embeddings
from integrations.azure_translator import translate_text
from api.tasks.schema import TaskType, TaskStatus
from config import settings
logger = logging.getLogger(__name__)


async def create_task(
    user_id: str,
    name: str,
    task_type: TaskType,
    file_ids: List[str],
    description: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    background_tasks: Optional[BackgroundTasks] = None
) -> Dict[str, Any]:
    """
    Create a new task.
    
    Args:
        user_id: User ID
        name: Task name
        task_type: Task type
        file_ids: File IDs to process
        description: Task description
        options: Task options
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict[str, Any]: Created task
    """
    # Validate file access
    for file_id in file_ids:
        file = await get_file_by_id(file_id)
        if not file:
            raise ValueError(f"File {file_id} not found")
        
        has_access = await check_file_access(file, user_id)
        if not has_access:
            raise ValueError(f"User {user_id} does not have access to file {file_id}")
    
    task_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Create task entry
    task = {
        "id": task_id,
        "user_id": user_id,
        "name": name,
        "description": description,
        "task_type": task_type,
        "file_ids": file_ids,
        "options": options or {},
        "status": TaskStatus.PENDING,
        "progress": 0.0,
        "result_file_ids": [],
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Save to database
    result = await create_item("tasks", task)
    
    # Start task processing in background
    if background_tasks:
        background_tasks.add_task(process_task, task_id, user_id)
    
    return result


async def update_task(
    task_id: str,
    user_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Update a task.
    
    Args:
        task_id: Task ID
        user_id: User ID
        name: New task name
        description: New task description
        options: New task options
        
    Returns:
        Dict[str, Any]: Updated task
    """
    # Get existing task
    task = await get_task_by_id(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")
    
    # Check ownership
    if task["user_id"] != user_id:
        raise ValueError(f"User {user_id} does not own task {task_id}")
    
    # Check if task can be updated
    if task["status"] != TaskStatus.PENDING:
        raise ValueError(f"Cannot update task {task_id} with status {task['status']}")
    
    # Update fields
    if name is not None:
        task["name"] = name
    
    if description is not None:
        task["description"] = description
    
    if options is not None:
        task["options"] = options
    
    # Update timestamp
    task["updated_at"] = datetime.utcnow().isoformat()
    
    # Save to database
    result = await replace_item("tasks", task_id, task)
    
    return result


async def cancel_task(task_id: str, user_id: str) -> Dict[str, Any]:
    """
    Cancel a task.
    
    Args:
        task_id: Task ID
        user_id: User ID
        
    Returns:
        Dict[str, Any]: Updated task
    """
    # Get existing task
    task = await get_task_by_id(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")
    
    # Check ownership
    if task["user_id"] != user_id:
        raise ValueError(f"User {user_id} does not own task {task_id}")
    
    # Check if task can be cancelled
    if task["status"] not in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
        raise ValueError(f"Cannot cancel task {task_id} with status {task['status']}")
    
    # Update status
    task["status"] = TaskStatus.CANCELLED
    task["updated_at"] = datetime.utcnow().isoformat()
    
    # Save to database
    result = await replace_item("tasks", task_id, task)
    
    return result


async def delete_task(task_id: str, user_id: str) -> None:
    """
    Delete a task.
    
    Args:
        task_id: Task ID
        user_id: User ID
    """
    # Get existing task
    task = await get_task_by_id(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")
    
    # Check ownership
    if task["user_id"] != user_id:
        raise ValueError(f"User {user_id} does not own task {task_id}")
    
    # Delete task
    await delete_item("tasks", task_id, task_id)


async def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a task by ID.
    
    Args:
        task_id: Task ID
        
    Returns:
        Optional[Dict[str, Any]]: Task if found, None otherwise
    """
    return await read_item("tasks", task_id, task_id)


async def check_task_access(task: Dict[str, Any], user_id: str) -> bool:
    """
    Check if a user has access to a task.
    
    Args:
        task: Task entry
        user_id: User ID
        
    Returns:
        bool: True if the user has access, False otherwise
    """
    # User owns the task
    return task["user_id"] == user_id


async def get_user_tasks(
    user_id: str,
    task_type: Optional[TaskType] = None,
    status: Optional[TaskStatus] = None,
    file_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get tasks owned by a user.
    
    Args:
        user_id: User ID
        task_type: Optional task type filter
        status: Optional status filter
        file_id: Optional file ID filter
        page: Page number
        page_size: Page size
        
    Returns:
        Tuple[List[Dict[str, Any]], int]: Tasks and total count
    """
    # Build query
    query = "SELECT * FROM c WHERE c.user_id = @user_id"
    parameters = [{"name": "@user_id", "value": user_id}]
    
    if task_type:
        query += " AND c.task_type = @task_type"
        parameters.append({"name": "@task_type", "value": task_type})
    
    if status:
        query += " AND c.status = @status"
        parameters.append({"name": "@status", "value": status})
    
    if file_id:
        query += " AND ARRAY_CONTAINS(c.file_ids, @file_id)"
        parameters.append({"name": "@file_id", "value": file_id})
    
    query += " ORDER BY c.created_at DESC"
    
    # Execute query
    return await query_items_with_pagination(
        settings.TASKS_CONTAINER_NAME,
        query,
        parameters,
        page,
        page_size
    )


async def get_task_result(task_id: str, user_id: str) -> Dict[str, Any]:
    """
    Get task result.
    
    Args:
        task_id: Task ID
        user_id: User ID
        
    Returns:
        Dict[str, Any]: Task result
    """
    # Get existing task
    task = await get_task_by_id(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")
    
    # Check ownership
    if task["user_id"] != user_id:
        raise ValueError(f"User {user_id} does not own task {task_id}")
    
    # Check if task is completed
    if task["status"] != TaskStatus.COMPLETED:
        raise ValueError(f"Task {task_id} is not completed")
    
    # Query task result
    results = await query_items(
        settings.TASK_RESULTS_CONTAINER_NAME,
        "SELECT * FROM c WHERE c.task_id = @task_id",
        [{"name": "@task_id", "value": task_id}]
    )
    
    if not results:
        raise ValueError(f"No results found for task {task_id}")
    
    return {
        "task_id": task_id,
        "result_type": task["task_type"],
        "content": results[0]["content"],
        "file_ids": task["result_file_ids"]
    }


async def process_task(task_id: str, user_id: str) -> None:
    """
    Process a task in the background.
    
    Args:
        task_id: Task ID
        user_id: User ID
    """
    # Get task
    task = await get_task_by_id(task_id)
    if not task:
        logger.error(f"Task {task_id} not found")
        return
    
    # Update status to processing
    task["status"] = TaskStatus.PROCESSING
    task["started_at"] = datetime.utcnow().isoformat()
    task["updated_at"] = task["started_at"]
    await replace_item("tasks", task_id, task)
    
    try:
        # Process task based on type
        result_content = None
        result_file_ids = []
        
        if task["task_type"] == TaskType.TRANSLATE:
            result_content = await process_translate_task(task)
        elif task["task_type"] == TaskType.SUMMARIZE:
            result_content = await process_summarize_task(task)
        elif task["task_type"] == TaskType.BRAINSTORM:
            result_content = await process_brainstorm_task(task)
        elif task["task_type"] == TaskType.POWERPOINT:
            result_content, result_file_ids = await process_powerpoint_task(task)
        elif task["task_type"] == TaskType.GRAPHRAG:
            result_content = await process_graphrag_task(task)
        else:
            raise ValueError(f"Unknown task type: {task['task_type']}")
        
        # Create task result
        result = {
            "id": str(uuid.uuid4()),
            "task_id": task_id,
            "user_id": user_id,
            "content": result_content,
            "created_at": datetime.utcnow().isoformat()
        }
        
        await create_item("task_results", result)
        
        # Update task status
        task["status"] = TaskStatus.COMPLETED
        task["progress"] = 1.0
        task["result_file_ids"] = result_file_ids
        task["completed_at"] = datetime.utcnow().isoformat()
        task["updated_at"] = task["completed_at"]
        await replace_item("tasks", task_id, task)
        
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {str(e)}")
        
        # Update task status to failed
        task["status"] = TaskStatus.FAILED
        task["error_message"] = str(e)
        task["updated_at"] = datetime.utcnow().isoformat()
        await replace_item("tasks", task_id, task)


async def process_translate_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a translation task.
    
    Args:
        task: Task entry
        
    Returns:
        Dict[str, Any]: Task result
    """
    # Get options
    options = task["options"]
    target_language = options.get("target_language", "en")
    source_language = options.get("source_language")
    
    # Get file content
    results = {}
    
    for file_id in task["file_ids"]:
        file = await get_file_by_id(file_id)
        if not file:
            continue
        
        # Download file content
        content, _, _ = await get_file_content(file_id, file["blob_path"])
        text_content = content.read().decode("utf-8")
        
        # Translate text
        translated_text = await translate_text(
            text_content,
            target_language,
            source_language
        )
        
        results[file_id] = {
            "original_filename": file["filename"],
            "translated_text": translated_text
        }
    
    return results


async def process_summarize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a summarization task.
    
    Args:
        task: Task entry
        
    Returns:
        Dict[str, Any]: Task result
    """
    # Get options
    options = task["options"]
    max_length = options.get("max_length")
    min_length = options.get("min_length")
    
    # Get file content
    results = {}
    
    for file_id in task["file_ids"]:
        file = await get_file_by_id(file_id)
        if not file:
            continue
        
        # Download file content
        content, _, _ = await get_file_content(file_id, file["blob_path"])
        text_content = content.read().decode("utf-8")
        
        # Generate summary
        summary = await generate_summary(
            text_content,
            max_length=max_length,
            min_length=min_length
        )
        
        results[file_id] = {
            "original_filename": file["filename"],
            "summary": summary
        }
    
    return results


async def process_brainstorm_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a brainstorming task.
    
    Args:
        task: Task entry
        
    Returns:
        Dict[str, Any]: Task result
    """
    # Get options
    options = task["options"]
    topic = options.get("topic", "")
    num_ideas = options.get("num_ideas", 5)
    
    # Get file content for context
    context = ""
    
    for file_id in task["file_ids"]:
        file = await get_file_by_id(file_id)
        if not file:
            continue
        
        # Download file content
        content, _, _ = await get_file_content(file_id, file["blob_path"])
        text_content = content.read().decode("utf-8")
        
        # Add to context
        context += text_content + "\n\n"
    
    # Generate embeddings for RAG
    embeddings = await generate_embeddings(context)
    
    # In a real implementation, this would use the embeddings for retrieval
    # For this example, we just return a mock result
    ideas = [
        f"Idea {i+1} for {topic}" for i in range(num_ideas)
    ]
    
    return {
        "topic": topic,
        "ideas": ideas,
        "context_files": [file_id for file_id in task["file_ids"]]
    }


async def process_powerpoint_task(task: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Process a PowerPoint generation task.
    
    Args:
        task: Task entry
        
    Returns:
        Tuple[Dict[str, Any], List[str]]: Task result and result file IDs
    """
    # Get options
    options = task["options"]
    title = options.get("title", "Presentation")
    num_slides = options.get("num_slides", 10)
    
    # Get file content for context
    context = ""
    
    for file_id in task["file_ids"]:
        file = await get_file_by_id(file_id)
        if not file:
            continue
        
        # Download file content
        content, _, _ = await get_file_content(file_id, file["blob_path"])
        text_content = content.read().decode("utf-8")
        
        # Add to context
        context += text_content + "\n\n"
    
    # In a real implementation, this would generate a PowerPoint file
    # For this example, we just return a mock result
    slides = [
        {
            "title": f"Slide {i+1}",
            "content": f"Content for slide {i+1}"
        } for i in range(num_slides)
    ]
    
    # In a real implementation, this would create a file in blob storage
    # and return the file ID
    result_file_ids = []
    
    return {
        "title": title,
        "slides": slides,
        "context_files": [file_id for file_id in task["file_ids"]]
    }, result_file_ids


async def process_graphrag_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a GraphRAG task.
    
    Args:
        task: Task entry
        
    Returns:
        Dict[str, Any]: Task result
    """
    # In a real implementation, this would call the GraphRAG microservice
    # For this example, we just return a mock result
    return {
        "graph": {
            "nodes": [
                {"id": "node1", "label": "Node 1"},
                {"id": "node2", "label": "Node 2"},
                {"id": "node3", "label": "Node 3"}
            ],
            "edges": [
                {"source": "node1", "target": "node2", "label": "relates to"},
                {"source": "node2", "target": "node3", "label": "contains"}
            ]
        },
        "context_files": [file_id for file_id in task["file_ids"]]
    }


async def query_items(
    container_name: str,
    query: str,
    parameters: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Query items from a container.
    
    Args:
        container_name: Container name
        query: SQL query
        parameters: Query parameters
        
    Returns:
        List[Dict[str, Any]]: Query results
    """
    from services.session import query_items as session_query_items
    return await session_query_items(container_name, query, parameters)
