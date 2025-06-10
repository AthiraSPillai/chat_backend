"""
Chat Sessions API routes for FastAPI Azure Backend.

This module defines routes for chat-related operations.
"""

from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks

from api.auth.dependency import get_current_active_user
from api.chat.schema import (
    ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse, ChatSessionListResponse,
    MessageCreate, MessageResponse, ChatHistoryResponse, ChatCompletionRequest,
    ChatCompletionResponse, ChatSessionStatus
)
from api.chat.dependency import (
    get_chat_status_filter, get_chat_tags_filter, get_pagination_params,
    get_message_pagination_params, get_user_chat_session
)
from services.chat import (
    create_chat_session, update_chat_session, delete_chat_session,
    get_user_chat_sessions, get_chat_history, create_message,
    generate_chat_completion
)
from services.prompt import PromptService # New import
from dependencies.cosmos import get_prompt_service # New import
from utils.pagination import PaginationParams
from utils.response import SuccessResponse

router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_new_chat_session(
    session_create: ChatSessionCreate,
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> ChatSessionResponse:
    """
    Create a new chat session.
    
    Args:
        session_create: Chat session creation data
        current_user: Current authenticated user
        
    Returns:
        ChatSessionResponse: Created chat session
    """
    # Create chat session in database
    session = await create_chat_session(
        user_id=current_user.id,
        title=session_create.title,
        description=session_create.description,
        tags=session_create.tags,
        system_prompt=session_create.system_prompt
    )
    
    return ChatSessionResponse(**session)


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_chat_sessions(
    current_user: Annotated[dict, Depends(get_current_active_user)],
    status: Optional[ChatSessionStatus] = Depends(get_chat_status_filter),
    tags: Optional[List[str]] = Depends(get_chat_tags_filter),
    pagination: PaginationParams = Depends(get_pagination_params)
) -> ChatSessionListResponse:
    """
    List chat sessions owned by the current user.
    
    Args:
        status: Optional status filter
        tags: Optional tags filter
        pagination: Pagination parameters
        current_user: Current authenticated user
        
    Returns:
        ChatSessionListResponse: Paginated list of chat sessions
    """
    sessions, total = await get_user_chat_sessions(
        user_id=current_user.id,
        status=status,
        tags=tags,
        page=pagination.page,
        page_size=pagination.page_size
    )
    
    pages = (total + pagination.page_size - 1) // pagination.page_size
    
    return ChatSessionListResponse(
        items=sessions,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        pages=pages
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session: Annotated[dict, Depends(get_user_chat_session)]
) -> ChatSessionResponse:
    """
    Get chat session details by ID.
    
    Args:
        session: Chat session from dependency
        
    Returns:
        ChatSessionResponse: Chat session details
    """
    return ChatSessionResponse(**session)


@router.put("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session_details(
    session_update: ChatSessionUpdate,
    session: Annotated[dict, Depends(get_user_chat_session)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> ChatSessionResponse:
    """
    Update chat session details.
    
    Args:
        session_update: Chat session update data
        session: Chat session from dependency
        current_user: Current authenticated user
        
    Returns:
        ChatSessionResponse: Updated chat session details
    """
    updated_session = await update_chat_session(
        session_id=session["id"],
        user_id=current_user.id,
        title=session_update.title,
        description=session_update.description,
        tags=session_update.tags,
        system_prompt=session_update.system_prompt,
        status=session_update.status
    )
    
    return ChatSessionResponse(**updated_session)


@router.delete("/sessions/{session_id}", response_model=SuccessResponse)
async def delete_user_chat_session(
    session: Annotated[dict, Depends(get_user_chat_session)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> SuccessResponse:
    """
    Delete a chat session.
    
    Args:
        session: Chat session from dependency
        current_user: Current authenticated user
        
    Returns:
        SuccessResponse: Success message
    """
    await delete_chat_session(session["id"], current_user.id)
    
    return SuccessResponse(message="Chat session deleted successfully")


@router.get("/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_session_history(
    session: Annotated[dict, Depends(get_user_chat_session)],
    pagination: Annotated[dict, Depends(get_message_pagination_params)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> ChatHistoryResponse:
    """
    Get chat session history.
    
    Args:
        session: Chat session from dependency
        pagination: Message pagination parameters
        current_user: Current authenticated user
        
    Returns:
        ChatHistoryResponse: Chat session history
    """
    messages, total, has_more = await get_chat_history(
        session_id=session["id"],
        user_id=current_user.id,
        limit=pagination["limit"],
        before_id=pagination["before_id"],
        after_id=pagination["after_id"]
    )
    
    return ChatHistoryResponse(
        session=ChatSessionResponse(**session),
        messages=messages,
        has_more=has_more,
        total_messages=total
    )


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def create_chat_message(
    message_create: MessageCreate,
    session: Annotated[dict, Depends(get_user_chat_session)],
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> MessageResponse:
    """
    Create a new message in a chat session.
    
    Args:
        message_create: Message creation data
        session: Chat session from dependency
        current_user: Current authenticated user
        
    Returns:
        MessageResponse: Created message
    """
    message = await create_message(
        session_id=session["id"],
        user_id=current_user.id,
        role=message_create.role,
        content=message_create.content
    )
    
    return MessageResponse(**message)


@router.post("/completions", response_model=ChatCompletionResponse)
async def generate_completion(
    completion_request: ChatCompletionRequest,
    current_user: Annotated[dict, Depends(get_current_active_user)],
    prompt_service: Annotated[PromptService, Depends(get_prompt_service)]
) -> ChatCompletionResponse:
    """
    Generate a chat completion.
    
    Args:
        completion_request: Chat completion request
        current_user: Current authenticated user
        prompt_service: PromptService instance for retrieving prompts
        
    Returns:
        ChatCompletionResponse: Generated completion
    """
    completion = await generate_chat_completion(
        user_id=current_user.id,
        messages=completion_request.messages,
        role_id=completion_request.role_id, # Pass role_id
        task_id=completion_request.task_id, # Pass task_id
        system_prompt=completion_request.system_prompt,
        temperature=completion_request.temperature,
        max_tokens=completion_request.max_tokens,
        stop=completion_request.stop,
        file_ids=completion_request.file_ids,
        prompt_service=prompt_service # Pass prompt_service
    )
    
    return completion


