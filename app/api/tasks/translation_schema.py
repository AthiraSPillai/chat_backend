from pydantic import BaseModel, Field
from typing import Optional

class DocumentTranslationRequest(BaseModel):
    file_id: str = Field(..., description="ID of the document file in Azure Blob Storage")
    target_language: str = Field(..., description="Target language for translation (e.g., es, fr, de)")
    output_format: Optional[str] = Field("text", description="Desired output format (e.g., text, markdown)")
    role_id: Optional[str] = Field(None, description="Role ID for prompt selection")
    task_id: Optional[str] = Field(None, description="Task ID for prompt selection")

class DocumentTranslationResponse(BaseModel):
    task_id: str = Field(..., description="ID of the translation task")
    status: str = Field(..., description="Status of the translation task")
    output_file_id: Optional[str] = Field(None, description="ID of the translated output file in Azure Blob Storage")
    message: Optional[str] = Field(None, description="Additional message or error details")


