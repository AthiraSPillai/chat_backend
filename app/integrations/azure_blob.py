from typing import Optional
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
from config import settings
import logging

logger = logging.getLogger(__name__)

blob_service_client: Optional[BlobServiceClient] = None

async def initialize_blob_client():
    global blob_service_client
    logger.info("Initializing Azure Blob Storage client")
    blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
    logger.info("Azure Blob Storage client initialized successfully")

async def close_blob_client():
    global blob_service_client
    if blob_service_client:
        logger.info("Closing Azure Blob Storage client")
        await blob_service_client.close()
        blob_service_client = None

async def upload_blob(container_name: str, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    container_client = blob_service_client.get_container_client(container_name)
    try:
        await container_client.create_container()
    except Exception as e:
        logger.info(f"Container {container_name} already exists or other error: {e}")
    
    blob_client = container_client.get_blob_client(blob_name)
    await blob_client.upload_blob(data, overwrite=True, content_settings={"contentType": content_type})
    return blob_client.url

async def download_blob(container_name: str, blob_name: str) -> Optional[bytes]:
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    try:
        download_stream = await blob_client.download_blob()
        return await download_stream.readall()
    except Exception as e:
        logger.error(f"Error downloading blob {blob_name} from container {container_name}: {e}")
        return None

async def delete_blob(container_name: str, blob_name: str) -> bool:
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    try:
        await blob_client.delete_blob()
        return True
    except Exception as e:
        logger.error(f"Error deleting blob {blob_name} from container {container_name}: {e}")
        return False

async def get_blob_url(container_name: str, blob_name: str) -> str:
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    return blob_client.url

async def generate_sas_url(container_name: str, blob_name: str, permission: str, expiry_minutes: int = 60) -> tuple[str, datetime]:
    """
    Generates a Shared Access Signature (SAS) URL for a blob.
    
    Args:
        container_name: The name of the container.
        blob_name: The name of the blob.
        permission: 'r' for read, 'w' for write, 'd' for delete, 'l' for list.
        expiry_minutes: The number of minutes until the SAS URL expires.
        
    Returns:
        A tuple containing the SAS URL and its expiration time.
    """
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    
    # Define permissions
    permissions = BlobSasPermissions(read='r' in permission, write='w' in permission, delete='d' in permission, list='l' in permission)
    
    # Set expiry time
    expiry_time = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    
    # Generate SAS token
    sas_token = generate_blob_sas(
        account_name=settings.AZURE_STORAGE_ACCOUNT_NAME,
        container_name=container_name,
        blob_name=blob_name,
        account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
        permission=permissions,
        expiry=expiry_time
    )
    
    # Construct the full SAS URL
    sas_url = f"{blob_client.url}?{sas_token}"
    
    return sas_url, expiry_time

async def get_blob_properties(container_name: str, blob_name: str):
    """
    Gets the properties of a blob.
    
    Args:
        container_name: The name of the container.
        blob_name: The name of the blob.
        
    Returns:
        The blob properties.
    """
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_name)
    return await blob_client.get_blob_properties()


