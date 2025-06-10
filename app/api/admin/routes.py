from api.auth.dependency import get_current_user
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, UploadFile, File, Security
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import logging

from api.admin.schema import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse,
    PromptCreate, PromptUpdate, PromptResponse, PromptListResponse,
    PromptContentUpdate, PromptContentResponse,
    MappingCreate, MappingUpdate, MappingResponse, MappingListResponse,
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
from services.prompt import PromptService
from services.mapping import MappingService
from services.prompt_import import PromptImportService # New import
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


# Role Management Endpoints

@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    current_admin: UserInDB = Depends(get_current_admin),
    # current_admin: UserInDB = Depends(validate_role_management_permission),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Create a new role.
    
    Args:
        role_data: Role data
        current_admin: Current admin user
        admin_service: Admin service
        
    Returns:
        RoleResponse: Created role
    """
    logger.info(f"Admin {current_admin.username} creating new role {role_data.name}")
    
    try:
        role = await admin_service.create_role(role_data, current_admin.id)
        return role
    except ValueError as e:
        logger.warning(f"Failed to create role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/roles", response_model=RoleListResponse)
async def list_roles(
    current_admin: UserInDB,
    # = Depends(validate_role_management_permission),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    name: Optional[str] = Query(None, description="Filter by name"),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    List roles.
    
    Args:
        page: Page number
        page_size: Page size
        name: Filter by name
        current_admin: Current admin user
        admin_service: Admin service
        
    Returns:
        RoleListResponse: List of roles
    """
    logger.info(f"Admin {current_admin.username} listing roles")
    
    pagination = get_page_params(page, page_size)
    
    filters = {}
    if name:
        filters["name"] = name
    
    roles, total = await admin_service.list_roles(
        pagination.get_skip(),
        pagination.get_limit(),
        filters
    )
    
    pagination_info = pagination.get_pagination_info(total)
    
    return {
        "items": roles,
        **pagination_info
    }


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    current_admin: UserInDB,

    role_id: str = Path(..., description="Role ID"),
    # = Depends(validate_role_management_permission),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Get role details.
    
    Args:
        role_id: Role ID
        current_admin: Current admin user
        admin_service: Admin service
        
    Returns:
        RoleResponse: Role details
    """
    logger.info(f"Admin {current_admin.username} getting role {role_id}")
    
    role = await admin_service.get_role(role_id)
    
    if not role:
        logger.warning(f"Role {role_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )
    
    return role


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_data: RoleUpdate,
    role_id: str = Path(..., description="Role ID"),
    current_admin: UserInDB = Depends(get_current_admin),
    #  Depends(validate_role_management_permission),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Update role.
    
    Args:
        role_data: Role data
        role_id: Role ID
        current_admin: Current admin user
        admin_service: Admin service
        
    Returns:
        RoleResponse: Updated role
    """
    logger.info(f"Admin {current_admin.username} updating role {role_id}")
    
    try:
        role = await admin_service.update_role(role_id, role_data)
        
        if not role:
            logger.warning(f"Role {role_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        return role
    except ValueError as e:
        logger.warning(f"Failed to update role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    current_admin: UserInDB,
    role_id: str = Path(..., description="Role ID"),
    # = Depends(validate_role_management_permission),
    admin_service: AdminService = Depends(get_admin_service)
):
    """
    Delete role.
    
    Args:
        role_id: Role ID
        current_admin: Current admin user
        admin_service: Admin service
    """
    logger.info(f"Admin {current_admin.username} deleting role {role_id}")
    
    result = await admin_service.delete_role(role_id)
    
    if not result:
        logger.warning(f"Role {role_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )


# Prompt Management Endpoints

@router.post("/prompts", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt_data: PromptCreate,
    # = Depends(validate_prompt_management_permission),
    prompt_service: PromptService = Depends(get_prompt_service),
    current_admin: UserInDB = Depends(get_current_admin)
):
    """
    Create a new prompt.
    
    Args:
        prompt_data: Prompt data
        current_admin: Current admin user
        prompt_service: Prompt service
        
    Returns:
        PromptResponse: Created prompt
    """
    logger.info(f"Admin {current_admin.username} creating new prompt {prompt_data.name}")
    
    try:
        prompt = await prompt_service.create_prompt(prompt_data, current_admin.id)
        return prompt
    except ValueError as e:
        logger.warning(f"Failed to create prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/prompts", response_model=PromptListResponse)
async def list_prompts(
    current_admin: UserInDB,
    # = Depends(validate_prompt_management_permission),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    name: Optional[str] = Query(None, description="Filter by name"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    prompt_service: PromptService = Depends(get_prompt_service)
):
    """
    List prompts.
    
    Args:
        page: Page number
        page_size: Page size
        name: Filter by name
        tag: Filter by tag
        current_admin: Current admin user
        prompt_service: Prompt service
        
    Returns:
        PromptListResponse: List of prompts
    """
    logger.info(f"Admin {current_admin.username} listing prompts")
    
    pagination = get_page_params(page, page_size)
    
    filters = {}
    if name:
        filters["name"] = name
    if tag:
        filters["tag"] = tag
    
    prompts, total = await prompt_service.list_prompts(
        pagination.get_skip(),
        pagination.get_limit(),
        filters
    )
    
    pagination_info = pagination.get_pagination_info(total)
    
    return {
        "items": prompts,
        **pagination_info
    }


@router.get("/prompts/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
     current_admin: UserInDB,
    prompt_id: str = Path(..., description="Prompt ID"),
   
    # = Depends(validate_prompt_management_permission),
    prompt_service: PromptService = Depends(get_prompt_service)
):
    """
    Get prompt details.
    
    Args:
        prompt_id: Prompt ID
        current_admin: Current admin user
        prompt_service: Prompt service
        
    Returns:
        PromptResponse: Prompt details
    """
    logger.info(f"Admin {current_admin.username} getting prompt {prompt_id}")
    
    prompt = await prompt_service.get_prompt(prompt_id)
    
    if not prompt:
        logger.warning(f"Prompt {prompt_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    
    return prompt


@router.put("/prompts/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    current_admin: UserInDB,

    prompt_data: PromptUpdate,
    prompt_id: str = Path(..., description="Prompt ID"),
    # = Depends(validate_prompt_management_permission),
    prompt_service: PromptService = Depends(get_prompt_service)
):
    """
    Update prompt.
    
    Args:
        prompt_data: Prompt data
        prompt_id: Prompt ID
        current_admin: Current admin user
        prompt_service: Prompt service
        
    Returns:
        PromptResponse: Updated prompt
    """
    logger.info(f"Admin {current_admin.username} updating prompt {prompt_id}")
    
    try:
        prompt = await prompt_service.update_prompt(prompt_id, prompt_data)
        
        if not prompt:
            logger.warning(f"Prompt {prompt_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )
        
        return prompt
    except ValueError as e:
        logger.warning(f"Failed to update prompt: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    current_admin: UserInDB ,
    prompt_id: str = Path(..., description="Prompt ID"),
    # = Depends(validate_prompt_management_permission),
    prompt_service: PromptService = Depends(get_prompt_service)
):
    """
    Delete prompt.
    
    Args:
        prompt_id: Prompt ID
        current_admin: Current admin user
        prompt_service: Prompt service
    """
    logger.info(f"Admin {current_admin.username} deleting prompt {prompt_id}")
    
    result = await prompt_service.delete_prompt(prompt_id)
    
    if not result:
        logger.warning(f"Prompt {prompt_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )


@router.get("/prompts/{prompt_id}/content", response_model=PromptContentResponse)
async def get_prompt_content(
    current_admin: UserInDB,
    prompt_id: str = Path(..., description="Prompt ID"),
    version: Optional[int] = Query(None, description="Prompt version"),
    
    # = Depends(validate_prompt_management_permission),
    prompt_service: PromptService = Depends(get_prompt_service)
):
    """
    Get prompt content.
    
    Args:
        prompt_id: Prompt ID
        version: Prompt version
        current_admin: Current admin user
        prompt_service: Prompt service
        
    Returns:
        PromptContentResponse: Prompt content
    """
    logger.info(f"Admin {current_admin.username} getting content for prompt {prompt_id}")
    
    content = await prompt_service.get_prompt_content(prompt_id, version)
    
    if not content:
        logger.warning(f"Prompt content for {prompt_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt content not found"
        )
    
    return content


@router.put("/prompts/{prompt_id}/content", response_model=PromptResponse)
async def update_prompt_content(
    content_data: PromptContentUpdate,
    current_admin: UserInDB ,
    # = Depends(validate_prompt_management_permission),
    prompt_id: str = Path(..., description="Prompt ID"),
    create_new_version: bool = Query(True, description="Create new version"),
    # = Depends(validate_prompt_management_permission),
    prompt_service: PromptService = Depends(get_prompt_service)
):
    """
    Update prompt content.
    
    Args:
        prompt_id: Prompt ID
        content_data: Prompt content data
        create_new_version: Whether to create a new version
        current_admin: Current admin user
        prompt_service: Prompt service
        
    Returns:
        PromptResponse: Updated prompt
    """
    logger.info(f"Admin {current_admin.username} updating content for prompt {prompt_id}")
    
    try:
        prompt = await prompt_service.update_prompt_content(
            prompt_id,
            content_data.content,
            create_new_version
        )
        
        if not prompt:
            logger.warning(f"Prompt {prompt_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )
        
        return prompt
    except ValueError as e:
        logger.warning(f"Failed to update prompt content: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Mapping Management Endpoints

@router.post("/mappings", response_model=MappingResponse, status_code=status.HTTP_201_CREATED)
async def create_mapping(
    mapping_data: MappingCreate,
    current_admin: UserInDB = Depends(get_current_admin),
    # = Depends(validate_mapping_management_permission),
    mapping_service: MappingService = Depends(MappingService)
):
    """
    Create a new mapping.
    
    Args:
        mapping_data: Mapping data
        current_admin: Current admin user
        mapping_service: Mapping service
        
    Returns:
        MappingResponse: Created mapping
    """
    logger.info(f"Admin {current_admin.username} creating new mapping")
    
    try:
        mapping = await mapping_service.create_mapping(mapping_data, current_admin.id)
        return mapping
    except ValueError as e:
        logger.warning(f"Failed to create mapping: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/mappings", response_model=MappingListResponse)
async def list_mappings(
    current_admin: UserInDB ,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Page size"),
    role_id: Optional[str] = Query(None, description="Filter by role ID"),
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    prompt_id: Optional[str] = Query(None, description="Filter by prompt ID"),
    
    # = Depends(validate_mapping_management_permission),
    mapping_service: MappingService = Depends()
):
    """
    List mappings.
    
    Args:
        page: Page number
        page_size: Page size
        role_id: Filter by role ID
        task_id: Filter by task ID
        prompt_id: Filter by prompt ID
        current_admin: Current admin user
        mapping_service: Mapping service
        
    Returns:
        MappingListResponse: List of mappings
    """
    logger.info(f"Admin {current_admin.username} listing mappings")
    
    pagination = get_page_params(page, page_size)
    
    filters = {}
    if role_id:
        filters["role_id"] = role_id
    if task_id:
        filters["task_id"] = task_id
    if prompt_id:
        filters["prompt_id"] = prompt_id
    
    mappings, total = await mapping_service.list_mappings(
        pagination.get_skip(),
        pagination.get_limit(),
        filters
    )
    
    pagination_info = pagination.get_pagination_info(total)
    
    return {
        "items": mappings,
        **pagination_info
    }


@router.get("/mappings/{mapping_id}", response_model=MappingResponse)
async def get_mapping(
    current_admin: UserInDB ,

    mapping_id: str = Path(..., description="Mapping ID"),
    # = Depends(validate_mapping_management_permission),
    mapping_service: MappingService = Depends()
):
    """
    Get mapping details.
    
    Args:
        mapping_id: Mapping ID
        current_admin: Current admin user
        mapping_service: Mapping service
        
    Returns:
        MappingResponse: Mapping details
    """
    logger.info(f"Admin {current_admin.username} getting mapping {mapping_id}")
    
    mapping = await mapping_service.get_mapping(mapping_id)
    
    if not mapping:
        logger.warning(f"Mapping {mapping_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found"
        )
    
    return mapping


@router.put("/mappings/{mapping_id}", response_model=MappingResponse)
async def update_mapping(
    current_admin: UserInDB ,
    mapping_data: MappingUpdate,
    mapping_id: str = Path(..., description="Mapping ID"),
    # = Depends(validate_mapping_management_permission),
    mapping_service: MappingService = Depends()
):
    """
    Update mapping.
    
    Args:
        mapping_data: Mapping data
        mapping_id: Mapping ID
        current_admin: Current admin user
        mapping_service: Mapping service
        
    Returns:
        MappingResponse: Updated mapping
    """
    logger.info(f"Admin {current_admin.username} updating mapping {mapping_id}")
    
    try:
        mapping = await mapping_service.update_mapping(mapping_id, mapping_data)
        
        if not mapping:
            logger.warning(f"Mapping {mapping_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mapping not found"
            )
        
        return mapping
    except ValueError as e:
        logger.warning(f"Failed to update mapping: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/mappings/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(
    mapping_id: str = Path(..., description="Mapping ID"),
    current_admin: UserInDB = Depends(get_current_admin),
    # current_admin: UserInDB = Depends(validate_mapping_management_permission),
    mapping_service: MappingService = Depends()
):
    """
    Delete mapping.
    
    Args:
        mapping_id: Mapping ID
        current_admin: Current admin user
        mapping_service: Mapping service
    """
    logger.info(f"Admin {current_admin.username} deleting mapping {mapping_id}")
    
    result = await mapping_service.delete_mapping(mapping_id)
    
    if not result:
        logger.warning(f"Mapping {mapping_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mapping not found"
        )


# @router.post("/prompts/upload_excel", status_code=status.HTTP_200_OK)
# async def upload_prompts_excel(
#     current_admin: UserInDB = Depends(get_current_admin),
#     prompt_import_service: PromptImportService = Depends(),
#     file: UploadFile = File(..., description="Excel file containing prompt definitions")
#     # current_admin: UserInDB = Depends(validate_prompt_management_permission),
#     # prompt_import_service: PromptImportService = Depends(get_prompt_import_service)
# ):
#     """
#     Upload an Excel file to define prompts and their mappings to roles and tasks.
    
#     Args:
#         file: The Excel file to upload.
#         current_admin: The current authenticated admin user.
#         prompt_import_service: The service to handle prompt import logic.
        
#     Returns:
#         A success message upon successful upload and processing.
#     """
#     logger.info(f"Admin {current_admin.username} uploading Excel file for prompts: {file.filename}")
    
#     if not file.filename.endswith((".xlsx", ".xls")):
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Invalid file type. Only Excel files (.xlsx, .xls) are allowed."
#         )
    
#     try:
#         file_content = await file.read()
#         await prompt_import_service.process_excel_prompts(file_content, current_admin.id)
#         return create_success_response("Excel file uploaded and processed successfully.")
#     except ValueError as e:
#         logger.warning(f"Failed to process Excel file: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e)
#         )
#     except Exception as e:
#         logger.error(f"An unexpected error occurred during Excel file upload: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="An unexpected error occurred during file processing."
#         )


