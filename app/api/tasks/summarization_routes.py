from fastapi import APIRouter, Depends, status, HTTPException
from api.tasks.summarization_schema import DocumentSummarizationRequest, DocumentSummarizationResponse
from services.summarization import summarize_document
from api.auth.dependency import get_current_active_user
from services.prompt import PromptService # New import
from dependencies.cosmos import get_prompt_service # New import
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/summarize", response_model=DocumentSummarizationResponse, status_code=status.HTTP_202_ACCEPTED)
async def summarize_document_endpoint(
    request: DocumentSummarizationRequest,
    current_user: dict = Depends(get_current_active_user),
    prompt_service: PromptService = Depends(get_prompt_service) # Inject PromptService
) -> DocumentSummarizationResponse:
    """
    Initiates a document summarization task.
    """
    logger.info(f"User {current_user['username']} initiated summarization for file {request.file_id}")
    
    try:
        response = await summarize_document(
            request,
            current_user["id"],
            role_id=request.role_id, # Pass role_id
            task_id=request.task_id, # Pass task_id
            prompt_service=prompt_service # Pass prompt_service
        )
        return response
    except Exception as e:
        logger.error(f"Error initiating summarization task: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


