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


from services.session import SessionManager
from config import settings

# For auth/UI sessions
ui_session_manager = SessionManager(
    cosmos_url=settings.COSMOS_ENDPOINT,
    cosmos_key=settings.COSMOS_KEY,
    db_name=settings.COSMOS_DATABASE,
    container_name=settings.SESSION_CONTAINER_NAME  # your UI session container
)

# For chat sessions
chat_session_manager = SessionManager(
    cosmos_url=settings.COSMOS_ENDPOINT,
    cosmos_key=settings.COSMOS_KEY,
    db_name=settings.COSMOS_DATABASE,
    container_name=settings.CHAT_CONTAINER_NAME  # your chat session container
)

# Dependency injectors
def get_ui_session_manager() -> SessionManager:
    return ui_session_manager

def get_chat_session_manager() -> SessionManager:
    return chat_session_manager
