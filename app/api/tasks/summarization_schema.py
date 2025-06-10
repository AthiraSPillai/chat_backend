from pydantic import BaseModel, Field
from typing import Optional

class DocumentSummarizationRequest(BaseModel):
    file_id: str = Field(..., description="ID of the document file in Azure Blob Storage")
    output_format: Optional[str] = Field("text", description="Desired output format (e.g., text, markdown)")
    summary_length: Optional[str] = Field("medium", description="Desired summary length (e.g., short, medium, long)")
    role_id: Optional[str] = Field(None, description="Role ID for prompt selection")
    task_id: Optional[str] = Field(None, description="Task ID for prompt selection")

class DocumentSummarizationResponse(BaseModel):
    task_id: str = Field(..., description="ID of the summarization task")
    status: str = Field(..., description="Status of the summarization task")
    output_file_id: Optional[str] = Field(None, description="ID of the summarized output file in Azure Blob Storage")
    message: Optional[str] = Field(None, description="Additional message or error details")


