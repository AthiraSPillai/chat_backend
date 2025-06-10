"""
Chat Sessions API dependencies for FastAPI Azure Backend.

This module provides dependency injection functions for chat-related operations.
"""

from typing import Annotated, Optional, List
from fastapi import Depends, HTTPException, status, Query

from api.auth.dependency import get_current_active_user
from api.chat.schema import ChatSessionStatus
from services.chat import get_chat_session_by_id, check_chat_session_access
from utils.pagination import PaginationParams


async def get_chat_status_filter(
    status: Optional[ChatSessionStatus] = Query(None, description="Filter by chat session status")
) -> Optional[ChatSessionStatus]:
    """
    Dependency to get chat session status filter.
    
    Args:
        status: Optional status filter
        
    Returns:
        Optional[ChatSessionStatus]: The status filter or None
    """
    return status


async def get_chat_tags_filter(
    tags: Optional[List[str]] = Query(None, description="Filter by chat session tags")
) -> Optional[List[str]]:
    """
    Dependency to get chat session tags filter.
    
    Args:
        tags: Optional tags filter
        
    Returns:
        Optional[List[str]]: The tags filter or None
    """
    return tags


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


async def get_message_pagination_params(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of messages to return"),
    before_id: Optional[str] = Query(None, description="Return messages before this ID"),
    after_id: Optional[str] = Query(None, description="Return messages after this ID")
) -> dict:
    """
    Dependency to get message pagination parameters.
    
    Args:
        limit: Maximum number of messages to return
        before_id: Return messages before this ID
        after_id: Return messages after this ID
        
    Returns:
        dict: Message pagination parameters
    """
    return {
        "limit": limit,
        "before_id": before_id,
        "after_id": after_id
    }


async def get_user_chat_session(
    session_id: str,
    current_user: Annotated[dict, Depends(get_current_active_user)]
) -> dict:
    """
    Dependency to get a chat session owned by the current user.
    
    Args:
        session_id: Chat session ID
        current_user: Current authenticated user
        
    Returns:
        dict: The chat session if it exists and is owned by the user
        
    Raises:
        HTTPException: If the chat session doesn't exist or the user doesn't have access
    """
    session = await get_chat_session_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found"
        )
    
    # Check if the user has access to the chat session
    has_access = await check_chat_session_access(session, current_user.id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this chat session"
        )
    
    return session
