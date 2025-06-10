"""
Tasks API schemas for FastAPI Azure Backend.

This module defines Pydantic models for task-related requests and responses.
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class TaskType(str, Enum):
    """Task type enumeration."""
    TRANSLATE = "translate"
    SUMMARIZE = "summarize"
    BRAINSTORM = "brainstorm"
    POWERPOINT = "powerpoint"
    GRAPHRAG = "graphrag"


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TranslateOptions(BaseModel):
    """Options for translation tasks."""
    target_language: str = Field(..., description="Target language code")
    source_language: Optional[str] = Field(None, description="Source language code (auto-detect if not provided)")
    preserve_formatting: bool = Field(default=True, description="Whether to preserve formatting")
    glossary_id: Optional[str] = Field(None, description="Custom glossary ID")


class SummarizeOptions(BaseModel):
    """Options for summarization tasks."""
    max_length: Optional[int] = Field(None, description="Maximum summary length")
    min_length: Optional[int] = Field(None, description="Minimum summary length")
    format: str = Field(default="paragraph", description="Summary format (paragraph, bullets, etc.)")
    focus_areas: Optional[List[str]] = Field(None, description="Areas to focus on in the summary")


class BrainstormOptions(BaseModel):
    """Options for brainstorming tasks."""
    topic: str = Field(..., description="Brainstorming topic")
    num_ideas: int = Field(default=5, description="Number of ideas to generate")
    creativity_level: float = Field(default=0.7, description="Creativity level (0.0-1.0)")
    format: str = Field(default="bullets", description="Output format")


class PowerPointOptions(BaseModel):
    """Options for PowerPoint generation tasks."""
    title: str = Field(..., description="Presentation title")
    num_slides: int = Field(default=10, description="Number of slides to generate")
    theme: Optional[str] = Field(None, description="Presentation theme")
    include_speaker_notes: bool = Field(default=True, description="Whether to include speaker notes")
    outline: Optional[List[str]] = Field(None, description="Presentation outline")


class GraphRAGOptions(BaseModel):
    """Options for GraphRAG tasks."""
    query: str = Field(..., description="Query for the graph")
    depth: int = Field(default=2, description="Graph traversal depth")
    max_nodes: int = Field(default=50, description="Maximum number of nodes")
    include_relationships: bool = Field(default=True, description="Whether to include relationships")


class TaskOptions(BaseModel):
    """Task options model."""
    translate: Optional[TranslateOptions] = Field(None, description="Translation options")
    summarize: Optional[SummarizeOptions] = Field(None, description="Summarization options")
    brainstorm: Optional[BrainstormOptions] = Field(None, description="Brainstorming options")
    powerpoint: Optional[PowerPointOptions] = Field(None, description="PowerPoint generation options")
    graphrag: Optional[GraphRAGOptions] = Field(None, description="GraphRAG options")


class TaskBase(BaseModel):
    """Base task model."""
    name: str = Field(..., description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    task_type: TaskType = Field(..., description="Task type")
    file_ids: List[str] = Field(..., description="File IDs to process")
    options: Dict[str, Any] = Field(default_factory=dict, description="Task options")


class TaskCreate(TaskBase):
    """Task creation model."""
    class Config:
        schema_extra = {
            "example": {
                "name": "Translate Document",
                "description": "Translate financial report to Spanish",
                "task_type": "translate",
                "file_ids": ["file123"],
                "options": {
                    "target_language": "es",
                    "preserve_formatting": True
                }
            }
        }


class TaskUpdate(BaseModel):
    """Task update model."""
    name: Optional[str] = Field(None, description="Task name")
    description: Optional[str] = Field(None, description="Task description")
    options: Optional[Dict[str, Any]] = Field(None, description="Task options")


class TaskResponse(TaskBase):
    """Task response model."""
    id: str = Field(..., description="Task ID")
    user_id: str = Field(..., description="Owner user ID")
    status: TaskStatus = Field(..., description="Task status")
    progress: float = Field(..., description="Task progress (0.0-1.0)")
    result_file_ids: List[str] = Field(default_factory=list, description="Result file IDs")
    error_message: Optional[str] = Field(None, description="Error message if task failed")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "task123",
                "user_id": "user456",
                "name": "Translate Document",
                "description": "Translate financial report to Spanish",
                "task_type": "translate",
                "file_ids": ["file123"],
                "options": {
                    "target_language": "es",
                    "preserve_formatting": True
                },
                "status": "completed",
                "progress": 1.0,
                "result_file_ids": ["file789"],
                "created_at": "2025-06-08T12:00:00Z",
                "updated_at": "2025-06-08T12:05:00Z",
                "started_at": "2025-06-08T12:00:05Z",
                "completed_at": "2025-06-08T12:05:00Z"
            }
        }


class TaskInDB(TaskResponse):
    """Task model as stored in the database."""
    pass


class TaskListResponse(BaseModel):
    """Task list response model."""
    items: List[TaskResponse] = Field(..., description="List of tasks")
    total: int = Field(..., description="Total number of tasks")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    pages: int = Field(..., description="Total number of pages")


class TaskResult(BaseModel):
    """Task result model."""
    task_id: str = Field(..., description="Task ID")
    result_type: str = Field(..., description="Result type")
    content: Union[str, Dict[str, Any]] = Field(..., description="Result content")
    file_ids: List[str] = Field(default_factory=list, description="Result file IDs")


class TaskStatusUpdate(BaseModel):
    """Task status update model."""
    status: TaskStatus = Field(..., description="New task status")
    progress: Optional[float] = Field(None, description="Task progress (0.0-1.0)")
    error_message: Optional[str] = Field(None, description="Error message if task failed")
