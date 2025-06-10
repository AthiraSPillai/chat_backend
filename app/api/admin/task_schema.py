from pydantic import BaseModel, Field
from typing import Optional, List

class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    role_id: Optional[str] = None
    prompt_template: Optional[str] = Field(None, max_length=2000)

class TaskCreate(TaskBase):
    pass

class TaskUpdate(TaskBase):
    pass

class TaskInDB(TaskBase):
    id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


