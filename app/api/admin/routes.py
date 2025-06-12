from api.auth.dependency import get_current_user
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, UploadFile, File, Security
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import logging

from api.admin.schema import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    RoleAssignment, UserActivationUpdate
)
from api.admin.dependency import (
    get_current_admin,
    # validate_user_management_permission,
    # validate_role_management_permission,
    # validate_prompt_management_permission,
    # validate_mapping_management_permission
)
from api.auth.schema import UserInDB
from services.admin import AdminService
from api.admin.dependency import get_admin_service, get_prompt_service # New dependency
from utils.pagination import get_page_params
from utils.response import create_success_response, create_error_response

logger = logging.getLogger(__name__)

router = APIRouter( )


# User Management Endpoints

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_admin: UserInDB = Security(get_current_user, scopes=["admin"]),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Create a new user.
    
    Args:
        user_data: User data
        current_admin: Current admin user
        admin_service: Admin service
        
    Returns:
        UserResponse: Created user
    """
    logger.info(f"Admin {current_admin.username} creating new user {user_data.username}")
    
    try:
        user = await admin_service.create_user(user_data, current_admin.id)
        return user
    except ValueError as e:
        logger.warning(f"Failed to create user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/users", response_model=UserListResponse)
async def list_users(
    current_admin: UserInDB= Depends(get_current_admin),
    # = Depends(validate_user_management_permission),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    username: Optional[str] = Query(None, description="Filter by username"),
    email: Optional[str] = Query(None, description="Filter by email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_admin: Optional[bool] = Query(None, description="Filter by admin status"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    List users.
    
    Args:
        page: Page number
        page_size: Page size
        username: Filter by username
        email: Filter by email
        role: Filter by role
        is_admin: Filter by admin status
        active: Filter by active status
        current_admin: Current admin user
        admin_service: Admin service
        
    Returns:
        UserListResponse: List of users
    """
    logger.info(f"Admin {current_admin.username} listing users")
    
    pagination = get_page_params(page, page_size)
    
    filters = {}
    if username:
        filters["username"] = username
    if email:
        filters["email"] = email
    if role:
        filters["role"] = role
    if is_admin is not None:
        filters["is_admin"] = is_admin
    if active is not None:
        filters["active"] = active
    
    users, total = await admin_service.list_users(
        pagination.get_skip(),
        pagination.get_limit(),
        filters
    )
    pagination_info = pagination.get_pagination_info(total)
    
    return {
        "items": users,
        **pagination_info
    }


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str = Path(..., description="User ID"),
    current_admin: UserInDB = Depends(get_current_admin),
    # current_admin: UserInDB = Depends(validate_user_management_permission),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Get user details.
    
    Args:
        user_id: User ID
        current_admin: Current admin user
        admin_service: Admin service
        
    Returns:
        UserResponse: User details
    """
    logger.info(f"Admin {current_admin.username} getting user {user_id}")
    
    user = await admin_service.get_user(user_id)
    
    if not user:
        logger.warning(f"User {user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_data: UserUpdate,
    user_id: str = Path(..., description="User ID"),
    current_admin: UserInDB = Depends(get_current_admin),
    # current_admin: UserInDB = Depends(validate_user_management_permission),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Update user.
    
    Args:
        user_data: User data
        user_id: User ID
        current_admin: Current admin user
        admin_service: Admin service
        
    Returns:
        UserResponse: Updated user
    """
    logger.info(f"Admin {current_admin.username} updating user {user_id}")
    
    try:
        user = await admin_service.update_user(user_id, user_data)
        
        if not user:
            logger.warning(f"User {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
    except ValueError as e:
        logger.warning(f"Failed to update user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str = Path(..., description="User ID"),
    current_admin: UserInDB = Depends(get_current_admin),
    # current_admin: UserInDB = Depends(validate_user_management_permission),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Delete user.
    
    Args:
        user_id: User ID
        current_admin: Current admin user
        admin_service: Admin service
    """
    logger.info(f"Admin {current_admin.username} deleting user {user_id}")
    
    # Prevent self-deletion
    if user_id == current_admin.id:
        logger.warning(f"Admin {current_admin.username} attempted to delete own account")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    result = await admin_service.delete_user(user_id)
    
    if not result:
        logger.warning(f"User {user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.post("/users/{user_id}/activate", response_model=UserResponse)
async def activate_user(
    activation: UserActivationUpdate,
    user_id: str = Path(..., description="User ID"),
    current_admin: UserInDB = Depends(get_current_admin),
    # current_admin: UserInDB = Depends(validate_user_management_permission),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Activate or deactivate user.
    
    Args:
        activation: Activation data
        user_id: User ID
        current_admin: Current admin user
        admin_service: Admin service
        
    Returns:
        UserResponse: Updated user
    """
    action = "activating" if activation.active else "deactivating"
    logger.info(f"Admin {current_admin.username} {action} user {user_id}")
    
    # Prevent self-deactivation
    if not activation.active and user_id == current_admin.id:
        logger.warning(f"Admin {current_admin.username} attempted to deactivate own account")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user = await admin_service.update_user_activation(user_id, activation.active)
    
    if not user:
        logger.warning(f"User {user_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.post("/users/{user_id}/roles", response_model=UserResponse)
async def assign_role_to_user(
    role_assignment: RoleAssignment,
    user_id: str = Path(..., description="User ID"),
    current_admin: UserInDB = Depends(get_current_admin),
    # current_admin: UserInDB = Depends(validate_user_management_permission),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Assign role to user.
    
    Args:
        role_assignment: Role assignment data
        user_id: User ID
        current_admin: Current admin user
        admin_service: Admin service
        
    Returns:
        UserResponse: Updated user
    """
    logger.info(f"Admin {current_admin.username} assigning role to user {user_id}")
    
    try:
        user = await admin_service.assign_role_to_user(user_id, role_assignment.role_id)
        
        if not user:
            logger.warning(f"User {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
    except ValueError as e:
        logger.warning(f"Failed to assign role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/users/{user_id}/roles/{role_id}", response_model=UserResponse)
async def remove_role_from_user(
    current_admin: UserInDB,
    user_id: str = Path(..., description="User ID"),
    role_id: str = Path(..., description="Role ID"),
    # = Depends(validate_user_management_permission),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Remove role from user.
    
    Args:
        user_id: User ID
        role_id: Role ID
        current_admin: Current admin user
        admin_service: Admin service
        
    Returns:
        UserResponse: Updated user
    """
    logger.info(f"Admin {current_admin.username} removing role from user {user_id}")
    
    try:
        user = await admin_service.remove_role_from_user(user_id, role_id)
        
        if not user:
            logger.warning(f"User {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
    except ValueError as e:
        logger.warning(f"Failed to remove role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


