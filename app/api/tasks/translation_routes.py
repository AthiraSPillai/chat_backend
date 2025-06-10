from fastapi import APIRouter, Depends, status, HTTPException
from api.tasks.translation_schema import DocumentTranslationRequest, DocumentTranslationResponse
from services.translation import translate_document
from api.auth.dependency import get_current_active_user
from services.prompt import PromptService # New import
from dependencies.cosmos import get_prompt_service # New import
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/translate", response_model=DocumentTranslationResponse, status_code=status.HTTP_202_ACCEPTED)
async def translate_document_endpoint(
    request: DocumentTranslationRequest,
    current_user: dict = Depends(get_current_active_user),
    prompt_service: PromptService = Depends(get_prompt_service) # Inject PromptService
) -> DocumentTranslationResponse:
    """
    Initiates a document translation task.
    """
    logger.info(f"User {current_user['username']} initiated translation for file {request.file_id} to {request.target_language}")
    
    try:
        response = await translate_document(
            request,
            current_user["id"],
            role_id=request.role_id, # Pass role_id
            task_id=request.task_id, # Pass task_id
            prompt_service=prompt_service # Pass prompt_service
        )
        return response
    except Exception as e:
        logger.error(f"Error initiating translation task: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))




