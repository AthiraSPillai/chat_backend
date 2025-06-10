"""
Chat service for FastAPI Azure Backend.

This module provides functions for managing chat sessions and messages.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from integrations.azure_cosmos_db import create_item, read_item, replace_item, delete_item, query_items, query_items_with_pagination
from integrations.azure_openai import generate_chat_completion as openai_generate_chat_completion
from api.chat.schema import ChatSessionStatus, MessageRole
from services.prompt import PromptService # New import

logger = logging.getLogger(__name__)


async def create_chat_session(
    user_id: str,
    title: str,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    system_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new chat session.
    
    Args:
        user_id: User ID
        title: Session title
        description: Session description
        tags: Session tags
        system_prompt: System prompt
        
    Returns:
        Dict[str, Any]: Created chat session
    """
    session_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Create chat session entry
    session = {
        "id": session_id,
        "user_id": user_id,
        "title": title,
        "description": description,
        "tags": tags or [],
        "status": ChatSessionStatus.ACTIVE,
        "system_prompt": system_prompt,
        "message_count": 0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "last_message_at": None
    }
    
    # Save to database
    result = await create_item("chat_sessions", session)
    
    # If system prompt is provided, create a system message
    if system_prompt:
        await create_message(
            session_id=session_id,
            user_id=user_id,
            role=MessageRole.SYSTEM,
            content=system_prompt
        )
    
    return result


async def update_chat_session(
    session_id: str,
    user_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    status: Optional[ChatSessionStatus] = None
) -> Dict[str, Any]:
    """
    Update a chat session.
    
    Args:
        session_id: Session ID
        user_id: User ID
        title: New session title
        description: New session description
        tags: New session tags
        system_prompt: New system prompt
        status: New session status
        
    Returns:
        Dict[str, Any]: Updated chat session
    """
    # Get existing session
    session = await get_chat_session_by_id(session_id)
    if not session:
        raise ValueError(f"Chat session {session_id} not found")
    
    # Check ownership
    if session["user_id"] != user_id:
        raise ValueError(f"User {user_id} does not own chat session {session_id}")
    
    # Update fields
    if title is not None:
        session["title"] = title
    
    if description is not None:
        session["description"] = description
    
    if tags is not None:
        session["tags"] = tags
    
    if status is not None:
        session["status"] = status
    
    # Update system prompt if provided
    if system_prompt is not None and system_prompt != session.get("system_prompt"):
        session["system_prompt"] = system_prompt
        
        # Find existing system message
        system_messages = await query_items(
            "messages",
            "SELECT * FROM c WHERE c.session_id = @session_id AND c.role = \'system\'",
            [
                {"name": "@session_id", "value": session_id}
            ]
        )
        
        if system_messages:
            # Update existing system message
            system_message = system_messages[0]
            system_message["content"] = system_prompt
            system_message["updated_at"] = datetime.utcnow().isoformat()
            await replace_item("messages", system_message["id"], system_message)
        else:
            # Create new system message
            await create_message(
                session_id=session_id,
                user_id=user_id,
                role=MessageRole.SYSTEM,
                content=system_prompt
            )
    
    # Update timestamp
    session["updated_at"] = datetime.utcnow().isoformat()
    
    # Save to database
    result = await replace_item("chat_sessions", session_id, session)
    
    return result


async def delete_chat_session(session_id: str, user_id: str) -> None:
    """
    Delete a chat session.
    
    Args:
        session_id: Session ID
        user_id: User ID
    """
    # Get existing session
    session = await get_chat_session_by_id(session_id)
    if not session:
        raise ValueError(f"Chat session {session_id} not found")
    
    # Check ownership
    if session["user_id"] != user_id:
        raise ValueError(f"User {user_id} does not own chat session {session_id}")
    
    # Delete messages
    # In a real implementation, this would use a bulk delete operation
    messages = await query_items(
        "messages",
        "SELECT c.id FROM c WHERE c.session_id = @session_id",
        [{"name": "@session_id", "value": session_id}]
    )
    
    for message in messages:
        await delete_item("messages", message["id"], session_id)
    
    # Delete session
    await delete_item("chat_sessions", session_id, session_id)


async def get_chat_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a chat session by ID.
    
    Args:
        session_id: Session ID
        
    Returns:
        Optional[Dict[str, Any]]: Chat session if found, None otherwise
    """
    return await read_item("chat_sessions", session_id, session_id)


async def check_chat_session_access(session: Dict[str, Any], user_id: str) -> bool:
    """
    Check if a user has access to a chat session.
    
    Args:
        session: Chat session entry
        user_id: User ID
        
    Returns:
        bool: True if the user has access, False otherwise
    """
    # User owns the session
    return session["user_id"] == user_id


async def get_user_chat_sessions(
    user_id: str,
    status: Optional[ChatSessionStatus] = None,
    tags: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 10
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Get chat sessions owned by a user.
    
    Args:
        user_id: User ID
        status: Optional status filter
        tags: Optional tags filter
        page: Page number
        page_size: Page size
        
    Returns:
        Tuple[List[Dict[str, Any]], int]: Chat sessions and total count
    """
    # Build query
    query = "SELECT * FROM c WHERE c.user_id = @user_id"
    parameters = [{"name": "@user_id", "value": user_id}]
    
    if status:
        query += " AND c.status = @status"
        parameters.append({"name": "@status", "value": status})
    
    if tags:
        # Filter by any of the specified tags
        tag_conditions = []
        for i, tag in enumerate(tags):
            tag_param = f"@tag{i}"
            tag_conditions.append(f"ARRAY_CONTAINS(c.tags, {tag_param})")
            parameters.append({"name": tag_param, "value": tag})
        
        query += f" AND ({ ' OR '.join(tag_conditions) })"
    
    query += " ORDER BY c.last_message_at DESC, c.created_at DESC"
    
    # Execute query
    return await query_items_with_pagination(
        "chat_sessions",
        query,
        parameters,
        page,
        page_size
    )


async def create_message(
    session_id: str,
    user_id: str,
    role: MessageRole,
    content: Any
) -> Dict[str, Any]:
    """
    Create a new message in a chat session.
    
    Args:
        session_id: Session ID
        user_id: User ID
        role: Message role
        content: Message content
        
    Returns:
        Dict[str, Any]: Created message
    """
    # Get existing session
    session = await get_chat_session_by_id(session_id)
    if not session:
        raise ValueError(f"Chat session {session_id} not found")
    
    # Check ownership
    if session["user_id"] != user_id and role != MessageRole.SYSTEM:
        raise ValueError(f"User {user_id} does not own chat session {session_id}")
    
    message_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Create message entry
    message = {
        "id": message_id,
        "session_id": session_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Save to database
    result = await create_item("messages", message)
    
    # Update session
    session["message_count"] += 1
    session["last_message_at"] = now.isoformat()
    session["updated_at"] = now.isoformat()
    await replace_item("chat_sessions", session_id, session)
    
    return result


async def get_chat_history(
    session_id: str,
    user_id: str,
    limit: int = 50,
    before_id: Optional[str] = None,
    after_id: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int, bool]:
    """
    Get chat history for a session.
    
    Args:
        session_id: Session ID
        user_id: User ID
        limit: Maximum number of messages to return
        before_id: Return messages before this ID
        after_id: Return messages after this ID
        
    Returns:
        Tuple[List[Dict[str, Any]], int, bool]: Messages, total count, and whether there are more messages
    """
    # Get existing session
    session = await get_chat_session_by_id(session_id)
    if not session:
        raise ValueError(f"Chat session {session_id} not found")
    
    # Check ownership
    if session["user_id"] != user_id:
        raise ValueError(f"User {user_id} does not own chat session {session_id}")
    
    # Build query
    query = "SELECT * FROM c WHERE c.session_id = @session_id"
    parameters = [{"name": "@session_id", "value": session_id}]
    
    if before_id:
        # Get message to determine created_at
        before_message = await read_item("messages", before_id, session_id)
        if before_message:
            query += " AND c.created_at < @before_time"
            parameters.append({"name": "@before_time", "value": before_message["created_at"]})
    
    if after_id:
        # Get message to determine created_at
        after_message = await read_item("messages", after_id, session_id)
        if after_message:
            query += " AND c.created_at > @after_time"
            parameters.append({"name": "@after_time", "value": after_message["created_at"]})
    
    query += " ORDER BY c.created_at DESC"
    
    # Execute query
    messages = await query_items(
        "messages",
        query,
        parameters
    )
    
    # Limit results
    limited_messages = messages[:limit]
    has_more = len(messages) > limit
    
    # Sort by created_at ascending for client
    limited_messages.sort(key=lambda m: m["created_at"])
    
    return limited_messages, session["message_count"], has_more


async def generate_chat_completion(
    user_id: str,
    messages: List[Dict[str, Any]],
    role_id: Optional[str] = None, # New parameter
    task_id: Optional[str] = None, # New parameter
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    stop: Optional[List[str]] = None,
    file_ids: Optional[List[str]] = None,
    prompt_service: PromptService = None # New parameter for dependency injection
) -> Dict[str, Any]:
    """
    Generate a chat completion.
    
    Args:
        user_id: User ID
        messages: List of messages
        role_id: Role ID for prompt selection
        task_id: Task ID for prompt selection
        system_prompt: System prompt (overridden by role/task specific prompt if provided)
        temperature: Temperature for sampling
        max_tokens: Maximum number of tokens to generate
        stop: Stop sequences
        file_ids: File IDs to reference
        prompt_service: PromptService instance for retrieving prompts
        
    Returns:
        Dict[str, Any]: Generated completion
    """
    # If role_id and task_id are provided, try to fetch a specific prompt
    if role_id and task_id and prompt_service:
        role_task_prompt = await prompt_service.get_prompt_by_role_and_task(role_id, task_id)
        if role_task_prompt:
            system_prompt = role_task_prompt["content"]
            logger.info(f"Using role/task specific prompt for chat: {role_task_prompt['name']}")

    # Format messages for OpenAI
    formatted_messages = []
    
    # Add system prompt if provided
    if system_prompt:
        formatted_messages.append({
            "role": "system",
            "content": system_prompt
        })
    
    # Add user messages
    for message in messages:
        formatted_messages.append({
            "role": message["role"],
            "content": message["content"]
        })
    
    # Generate completion
    completion, usage = await openai_generate_chat_completion(
        formatted_messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stop=stop
    )
    
    # Create message object
    now = datetime.utcnow()
    message = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "role": "assistant",
        "content": completion,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    return {
        "message": message,
        "usage": usage
    }




