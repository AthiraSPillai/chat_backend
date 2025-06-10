import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from azure.cosmos.aio import CosmosClient

from api.auth.dependency import get_current_user
from api.auth.schema import UserInDB
from services.admin import AdminService
from services.prompt import PromptService
from services.mapping import MappingService
from services.prompt_import import PromptImportService
from dependencies.cosmos import get_container, get_cosmos_client

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_admin(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """
    Get the current admin user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserInDB: Current admin user
        
    Raises:
        HTTPException: If the user is not an admin
    """
    if not current_user.is_admin:
        logger.warning(f"Non-admin user {current_user.username} attempted to access admin endpoint")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return current_user


async def get_admin_service(
    cosmos_client: CosmosClient = Depends(get_cosmos_client)
) -> AdminService:
    """
    Dependency that provides the AdminService.
    """
    users_container = await get_container("users")
    roles_container = await get_container("roles")
    return AdminService(users_container, roles_container)


async def get_prompt_service(
    cosmos_client: CosmosClient = Depends(get_cosmos_client)
) -> PromptService:
    """
    Dependency that provides the PromptService.
    """
    return PromptService(cosmos_client)


# async def validate_user_management_permission(
#     current_admin: UserInDB = Depends(get_current_admin)
# ) -> UserInDB:
#     """
#     Validate that the current admin has user management permission.
    
#     Args:
#         current_admin: Current admin user
        
#     Returns:
#         UserInDB: Current admin user
        
#     Raises:
#         HTTPException: If the admin does not have user management permission
#     """
#     # if "admin:users" not in current_admin.permissions:
#     #     logger.warning(f"Admin user {current_admin.username} attempted to access user management without permission")
#     #     raise HTTPException(
#     #         status_code=status.HTTP_403_FORBIDDEN,
#     #         detail="User management permission required",
#     #     )
    
#     return current_admin


# async def validate_role_management_permission(
#     current_admin: UserInDB = Depends(get_current_admin)
# ) -> UserInDB:
#     """
#     Validate that the current admin has role management permission.
    
#     Args:
#         current_admin: Current admin user
        
#     Returns:
#         UserInDB: Current admin user
        
#     Raises:
#         HTTPException: If the admin does not have role management permission
#     """
#     if "admin:roles" not in current_admin.permissions:
#         logger.warning(f"Admin user {current_admin.username} attempted to access role management without permission")
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Role management permission required",
#         )
    
#     return current_admin


# async def validate_prompt_management_permission(
#     current_admin: UserInDB = Depends(get_current_admin)
# ) -> UserInDB:
#     """
#     Validate that the current admin has prompt management permission.
    
#     Args:
#         current_admin: Current admin user
        
#     Returns:
#         UserInDB: Current admin user
        
#     Raises:
#         HTTPException: If the admin does not have prompt management permission
#     """
#     if "admin:prompts" not in current_admin.permissions:
#         logger.warning(f"Admin user {current_admin.username} attempted to access prompt management without permission")
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Prompt management permission required",
#         )
    
#     return current_admin


# async def validate_mapping_management_permission(
#     current_admin: UserInDB = Depends(get_current_admin)
# ) -> UserInDB:
#     """
#     Validate that the current admin has mapping management permission.
    
#     Args:
#         current_admin: Current admin user
        
#     Returns:
#         UserInDB: Current admin user
        
#     Raises:
#         HTTPException: If the admin does not have mapping management permission
#     """
#     if "admin:mappings" not in current_admin.permissions:
#         logger.warning(f"Admin user {current_admin.username} attempted to access mapping management without permission")
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Mapping management permission required",
#         )
    
#     return current_admin





# async def get_prompt_import_service(
#     cosmos_client: CosmosClient = Depends(get_cosmos_client)
# ) -> PromptImportService:
#     """
#     Dependency that provides the PromptImportService.
#     """
#     return PromptImportService(PromptService(cosmos_client), MappingService(cosmos_client), cosmos_client)


