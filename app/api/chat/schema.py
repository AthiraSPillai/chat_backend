"""
Chat Sessions API schemas for FastAPI Azure Backend.

This module defines Pydantic models for chat-related requests and responses.
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message role enumeration."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class MessageType(str, Enum):
    """Message type enumeration."""
    TEXT = "text"
    FILE_REFERENCE = "file_reference"
    TASK_REFERENCE = "task_reference"
    FUNCTION_CALL = "function_call"
    FUNCTION_RESULT = "function_result"


class ChatSessionStatus(str, Enum):
    """Chat session status enumeration."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MessageContent(BaseModel):
    """Message content model."""
    type: MessageType = Field(..., description="Content type")
    text: Optional[str] = Field(None, description="Text content")
    file_id: Optional[str] = Field(None, description="Referenced file ID")
    task_id: Optional[str] = Field(None, description="Referenced task ID")
    function_name: Optional[str] = Field(None, description="Function name")
    function_args: Optional[Dict[str, Any]] = Field(None, description="Function arguments")
    function_result: Optional[Dict[str, Any]] = Field(None, description="Function result")

    @validator("text")
    def text_required_for_text_type(cls, v, values):
        if values.get("type") == MessageType.TEXT and v is None:
            raise ValueError("text is required for TEXT type")
        return v

    @validator("file_id")
    def file_id_required_for_file_reference(cls, v, values):
        if values.get("type") == MessageType.FILE_REFERENCE and v is None:
            raise ValueError("file_id is required for FILE_REFERENCE type")
        return v

    @validator("task_id")
    def task_id_required_for_task_reference(cls, v, values):
        if values.get("type") == MessageType.TASK_REFERENCE and v is None:
            raise ValueError("task_id is required for TASK_REFERENCE type")
        return v

    @validator("function_name", "function_args")
    def function_fields_required_for_function_call(cls, v, values):
        if values.get("type") == MessageType.FUNCTION_CALL and v is None:
            field_name = "function_name" if "function_name" not in values else "function_args"
            raise ValueError(f"{field_name} is required for FUNCTION_CALL type")
        return v

    @validator("function_result")
    def function_result_required_for_function_result(cls, v, values):
        if values.get("type") == MessageType.FUNCTION_RESULT and v is None:
            raise ValueError("function_result is required for FUNCTION_RESULT type")
        return v


class MessageBase(BaseModel):
    """Base message model."""
    role: MessageRole = Field(..., description="Message role")
    content: Union[str, List[MessageContent]] = Field(..., description="Message content")


class MessageCreate(MessageBase):
    """Message creation model."""
    class Config:
        schema_extra = {
            "example": {
                "role": "user",
                "content": "Can you analyze this financial report?"
            }
        }


class MessageResponse(MessageBase):
    """Message response model."""
    id: str = Field(..., description="Message ID")
    session_id: str = Field(..., description="Chat session ID")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "msg123",
                "session_id": "session456",
                "user_id": "user789",
                "role": "user",
                "content": "Can you analyze this financial report?",
                "created_at": "2025-06-08T12:00:00Z",
                "updated_at": None
            }
        }


class MessageInDB(MessageResponse):
    """Message model as stored in the database."""
    pass


class ChatSessionBase(BaseModel):
    """Base chat session model."""
    title: str = Field(..., description="Session title")
    description: Optional[str] = Field(None, description="Session description")
    tags: List[str] = Field(default_factory=list, description="Session tags")


class ChatSessionCreate(ChatSessionBase):
    """Chat session creation model."""
    system_prompt: Optional[str] = Field(None, description="System prompt")
    
    class Config:
        schema_extra = {
            "example": {
                "title": "Financial Report Analysis",
                "description": "Analysis of Q2 financial report",
                "tags": ["finance", "analysis"],
                "system_prompt": "You are a financial analyst assistant."
            }
        }


class ChatSessionUpdate(BaseModel):
    """Chat session update model."""
    title: Optional[str] = Field(None, description="Session title")
    description: Optional[str] = Field(None, description="Session description")
    tags: Optional[List[str]] = Field(None, description="Session tags")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    status: Optional[ChatSessionStatus] = Field(None, description="Session status")


class ChatSessionResponse(ChatSessionBase):
    """Chat session response model."""
    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="Owner user ID")
    status: ChatSessionStatus = Field(..., description="Session status")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    message_count: int = Field(..., description="Number of messages")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    last_message_at: Optional[datetime] = Field(None, description="Last message timestamp")
    ui_session_id: Optional[str] = Field(None, description="UI session ID for tracking")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "session123",
                "user_id": "user456",
                "title": "Financial Report Analysis",
                "description": "Analysis of Q2 financial report",
                "status": "active",
                "system_prompt": "You are a financial analyst assistant.",
                "tags": ["finance", "analysis"],
                "message_count": 10,
                "created_at": "2025-06-08T12:00:00Z",
                "updated_at": "2025-06-08T14:30:00Z",
                "last_message_at": "2025-06-08T14:30:00Z"
            }
        }


class ChatSessionInDB(ChatSessionResponse):
    """Chat session model as stored in the database."""
    pass


class ChatSessionListResponse(BaseModel):
    """Chat session list response model."""
    items: List[ChatSessionResponse] = Field(..., description="List of chat sessions")
    total: int = Field(..., description="Total number of chat sessions")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")


class ChatHistoryResponse(BaseModel):
    """Chat history response model."""
    session: ChatSessionResponse = Field(..., description="Chat session")
    messages: List[MessageResponse] = Field(..., description="List of messages")
    has_more: bool = Field(..., description="Whether there are more messages")
    total_messages: int = Field(..., description="Total number of messages")


class ChatCompletionRequest(BaseModel):
    """Chat completion request model."""
    messages: List[MessageCreate] = Field(..., description="List of messages")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    role_id: Optional[str] = Field(None, description="Role ID for prompt selection")
    task_id: Optional[str] = Field(None, description="Task ID for prompt selection")
    temperature: Optional[float] = Field(0.7, description="Temperature for sampling")
    max_tokens: Optional[int] = Field(None, description="Maximum number of tokens to generate")
    stop: Optional[List[str]] = Field(None, description="Stop sequences")
    file_ids: Optional[List[str]] = Field(None, description="File IDs to reference")
    
    class Config:
        schema_extra = {
            "example": {
                "messages": [
                    {
                        "role": "user",
                        "content": "Can you analyze this financial report?"
                    }
                ],
                "system_prompt": "You are a financial analyst assistant.",
                "temperature": 0.7,
                "file_ids": ["file123"],
                "role_id": "finance_analyst",
                "task_id": "report_analysis"
            }
        }


class ChatCompletionResponse(BaseModel):
    """Chat completion response model."""
    message: MessageResponse = Field(..., description="Generated message")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")


