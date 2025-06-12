from typing import List, Optional
from api.admin.prompt_schema import PromptContentResponse, PromptContentUpdate, PromptCreate, PromptListResponse, PromptResponse, PromptUpdate
from api.admin.dependency import get_current_admin
from api.auth.schema import UserInDB
from utils.pagination import get_page_params
from services.prompt import PromptService
from dependencies.cosmos import get_prompt_service
from fastapi import APIRouter, Depends, HTTPException, status, Query,Path
from api.admin.task_schema import TaskCreate, TaskUpdate, TaskInDB
from services.task_management import create_task, get_task_by_id, get_all_tasks, update_task, delete_task
from api.auth.dependency import get_current_active_user
from utils.response import SuccessResponse
import logging
logger = logging.getLogger(__name__)

router = APIRouter()


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
            detail=str(e))