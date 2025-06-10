from typing import Optional
from datetime import datetime
import uuid
import logging

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from integrations.azure_blob import download_blob, upload_blob
from integrations.azure_openai import generate_summary
from integrations.azure_cosmos_db import create_item # Import create_item directly
from api.tasks.summarization_schema import DocumentSummarizationRequest, DocumentSummarizationResponse
from services.prompt import PromptService # New import

logger = logging.getLogger(__name__)

async def summarize_document(
    request: DocumentSummarizationRequest,
    user_id: str,
    role_id: Optional[str] = None, # New parameter
    task_id: Optional[str] = None, # New parameter
    prompt_service: Optional[PromptService] = None # New parameter for dependency injection
) -> DocumentSummarizationResponse:
    """
    Summarizes a document from Azure Blob Storage and stores the summary.
    """
    task_internal_id = str(uuid.uuid4())
    output_file_id = None
    status_message = "pending"
    
    try:
        # 1. Download the content of the file from Azure Blob Storage
        file_content = await download_blob("documents", request.file_id)
        if not file_content:
            status_message = "failed"
            logger.error(f"File {request.file_id} not found in blob storage.")
            return DocumentSummarizationResponse(
                task_id=task_internal_id, status=status_message, message=f"File {request.file_id} not found."
            )
        
        text_content = file_content.decode("utf-8") # Assuming text content for summarization
        
        # Determine summary length parameters
        min_length = None
        max_length = None
        if request.summary_length == "short":
            max_length = 100
        elif request.summary_length == "medium":
            max_length = 300
        elif request.summary_length == "long":
            max_length = 800
            
        # Fetch role/task specific prompt if provided
        system_prompt = None
        if role_id and task_id and prompt_service:
            role_task_prompt = await prompt_service.get_prompt_by_role_and_task(role_id, task_id)
            if role_task_prompt:
                system_prompt = role_task_prompt["content"]
                logger.info(f"Using role/task specific prompt for summarization: {role_task_prompt['name']}")

        # 3. Use the generate_summary function from integrations/azure_openai.py
        summary = await generate_summary(text_content, max_length=max_length, min_length=min_length, system_prompt=system_prompt)
        
        # 4. Upload the summarized content back to Azure Blob Storage
        output_file_id = f"summary_{uuid.uuid4()}.txt"
        await upload_blob("summaries", output_file_id, summary.encode("utf-8"), "text/plain")
        
        # 5. Store the mapping between the input file and the output file in Cosmos DB
        await create_item("summarization_tasks", {
            "id": task_internal_id,
            "user_id": user_id,
            "input_file_id": request.file_id,
            "output_file_id": output_file_id,
            "status": "completed",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        })
        status_message = "completed"
        
    except Exception as e:
        status_message = "failed"
        logger.error(f"Error during document summarization task {task_internal_id}: {e}")
        # Log the task status in Cosmos DB even if it failed
        await create_item("summarization_tasks", {
            "id": task_internal_id,
            "user_id": user_id,
            "input_file_id": request.file_id,
            "output_file_id": output_file_id,
            "status": status_message,
            "message": str(e),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        })
        
    return DocumentSummarizationResponse(
        task_id=task_internal_id,
        status=status_message,
        output_file_id=output_file_id if status_message == "completed" else None,
        message="Document summarization completed successfully." if status_message == "completed" else "Document summarization failed."
    )


