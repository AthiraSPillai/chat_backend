from pydantic import BaseModel, Field
from typing import Optional, List

TASK_ID_TO_NAME = {
    1: "Summarization",
    2: "Translation",
    3: "Brainstorming",
    4: "PowerPoint Generation"
}
class TaskBase(BaseModel):
    task_id: int
    name: str = ""

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


