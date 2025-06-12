from pydantic import BaseModel, Field
from typing import Optional, List

class RoleBase(BaseModel):
    role_id: int = Field(..., ge=1, le=1000, description="Unique identifier for the role")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase):
    pass

class RoleInDB(RoleBase):
    id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


