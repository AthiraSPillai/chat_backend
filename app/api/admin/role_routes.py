from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.admin.role_schema import RoleCreate, RoleUpdate, RoleInDB
from services.role import create_role, get_role_by_id, get_all_roles, update_role, delete_role
from api.auth.dependency import get_current_active_user
from utils.response import SuccessResponse

router = APIRouter()

@router.post("/roles", response_model=RoleInDB, status_code=status.HTTP_201_CREATED)
async def create_new_role(
    role_data: RoleCreate,
    current_user: dict = Depends(get_current_active_user)
) -> RoleInDB:
    # Add admin check here if needed
    role = await create_role(role_data)
    return role

@router.get("/roles/{role_id}", response_model=RoleInDB)
async def get_role(
    role_id: str,
    current_user: dict = Depends(get_current_active_user)
) -> RoleInDB:
    role = await get_role_by_id(role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role

@router.get("/roles", response_model=List[RoleInDB])
async def list_roles(
    current_user: dict = Depends(get_current_active_user)
) -> List[RoleInDB]:
    roles = await get_all_roles()
    return roles

@router.put("/roles/{role_id}", response_model=RoleInDB)
async def update_existing_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: dict = Depends(get_current_active_user)
) -> RoleInDB:
    role = await update_role(role_id, role_data)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role

@router.delete("/roles/{role_id}", response_model=SuccessResponse)
async def delete_existing_role(
    role_id: str,
    current_user: dict = Depends(get_current_active_user)
) -> SuccessResponse:
    success = await delete_role(role_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return SuccessResponse(message="Role deleted successfully")


