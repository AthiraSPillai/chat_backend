from azure.cosmos.aio import CosmosClient
from integrations.azure_cosmos_db import cosmos_db_service
from services.prompt import PromptService

async def get_cosmos_client() -> CosmosClient:
    """
    Dependency that provides the Cosmos DB client.
    """
    if cosmos_db_service.client is None:
        raise ValueError("Cosmos DB client not initialized.")
    return cosmos_db_service.client

async def get_container(container_name: str):
    """
    Dependency that provides a Cosmos DB container client.
    """
    return await cosmos_db_service.get_container(container_name)

async def get_prompt_service() -> PromptService:
    """
    Dependency that provides the PromptService.
    """
    return PromptService(cosmos_db_service.client)


