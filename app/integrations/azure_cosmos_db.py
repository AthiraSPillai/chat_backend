from typing import Optional, Dict, Any, List, Tuple
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey, exceptions as cosmos_exceptions
from config import settings
import logging

logger = logging.getLogger(__name__)


class CosmosDBService:
    def __init__(self):
        self.client: Optional[CosmosClient] = None
        self.database = None
        self.containers: Dict[str, Any] = {}
        self._connected = False

    async def connect(self):
        """One-time initialization of Cosmos DB client and containers."""
        if self._connected:
            return  # Already initialized

        logger.info("Initializing Cosmos DB client and containers")
        self.client = CosmosClient(settings.COSMOS_ENDPOINT, credential=settings.COSMOS_KEY)
        self.database = self.client.get_database_client(settings.COSMOS_DATABASE)

        try:
            await self.database.read()
        except cosmos_exceptions.CosmosResourceNotFoundError:
            logger.info(f"Creating database: {settings.COSMOS_DATABASE}")
            self.database = await self.client.create_database_if_not_exists(
                settings.COSMOS_DATABASE,
                offer_throughput=3000
            )

        container_names = [
            settings.SESSION_CONTAINER_NAME, settings.FILES_CONTAINER_NAME ,settings.CHAT_CONTAINER_NAME,settings.TASKS_CONTAINER_NAME,
            settings.TASK_RESULTS_CONTAINER_NAME,settings.EMBEDDINGS_CONTAINER_NAME, settings.USERS_CONTAINER_NAME,settings.ROLES_CONTAINER_NAME,
            settings.REFRESH_TOKEN_CONTAINER_NAME, settings.TASKS_CONTAINER_NAME, settings.CHAT_MESSAGES_CONTAINER_NAME
        ]

        for name in container_names:
            if name in self.containers:
                continue  # Already loaded

            try:
                container = self.database.get_container_client(name)
                await container.read()
            except cosmos_exceptions.CosmosResourceNotFoundError:
                logger.info(f"Creating container: {name}")
                key_path = (
                    "/session_id" if name in ["session", "task_results"]
                    else "/id"
                )
                container = await self.database.create_container_if_not_exists(
                    id=name, partition_key=PartitionKey(path=key_path)
                )

            self.containers[name] = container

        self._connected = True

    async def close(self):
        """Close the Cosmos DB client."""
        if self.client:
            logger.info("Closing Cosmos DB client")
            await self.client.close()
            self.client = None
            self._connected = False

    async def get_container(self, name: str):
        await self.connect()
        if name not in self.containers:
            raise ValueError(f"Container '{name}' not initialized")
        return self.containers[name]

    async def create_item(self, container_name: str, item: Dict[str, Any]):
        container = await self.get_container(container_name)
        return await container.create_item(item)

    async def update_item_by_id(self, container_name: str, item_id: str, updated_item: Dict[str, Any]):
        container = await self.get_container(container_name)
        return await container.replace_item(item=item_id, body=updated_item)

    async def query_items(self, container_name: str, query: str, parameters: Optional[list] = None, partition_key=None):
        container = await self.get_container(container_name)
        query_iterable = container.query_items(
            query=query,
            parameters=parameters or [],
        )
        return [item async for item in query_iterable]

    async def query_items_with_pagination(
    self,
    container_name: str,
    query: str,
    parameters: Optional[list] = None,
    page: int = 1,
    page_size: int = 10,
    continuation_token: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
        container = await self.get_container(container_name)

        offset = (page - 1) * page_size

        if "WHERE" in query:
            count_query = f"SELECT VALUE COUNT(1) FROM c WHERE {query.split('WHERE', 1)[1]}"
        else:
            count_query = "SELECT VALUE COUNT(1) FROM c"

        count_result = await self.query_items(container_name, count_query, parameters)
        total_count = count_result[0] if count_result else 0

        paginated_query = f"{query} OFFSET {offset} LIMIT {page_size}"
        items = [item async for item in container.query_items(query=paginated_query, parameters=parameters)]
        return items, total_count
       
    
    async def delete_item_by_id(self, container_name: str, item_id: str, partition_key: str):
        container = await self.get_container(container_name)
        try:
            await container.delete_item(item=item_id, partition_key=partition_key)
            return True
        except cosmos_exceptions.CosmosResourceNotFoundError:
            logger.warning(f"Item with id {item_id} not found in container {container_name}")
        except Exception as e:
            logger.error(f"Error deleting item {item_id} from container {container_name}: {e}")


cosmos_db_service = CosmosDBService()

async def initialize_cosmos_client():
    await cosmos_db_service.connect()

async def close_cosmos_client():
    await cosmos_db_service.close()

async def get_container(container_name: str):
    return await cosmos_db_service.get_container(container_name)

async def create_item(container_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    return await cosmos_db_service.create_item(container_name, item)

async def read_item(container_name: str, item_id: str, partition_key: str) -> Optional[Dict[str, Any]]:
    query = f"SELECT * FROM c WHERE c.id = '{item_id}'"
    results = await cosmos_db_service.query_items(container_name, query, partition_key=partition_key)
    return results[0] if results else None

async def replace_item(container_name: str, item_id: str, item: Dict[str, Any]) -> Dict[str, Any]:
    return await cosmos_db_service.update_item_by_id(container_name, item_id, item)

async def delete_item(container_name: str, item_id: str, partition_key: str) -> bool:
    try:
        await cosmos_db_service.delete_item_by_id(container_name, item_id, partition_key)
        return True
    except cosmos_exceptions.CosmosResourceNotFoundError:
        return False
    except Exception as e:
        logger.error(f"Error deleting item {item_id} from container {container_name}: {e}")
        raise

async def query_items_with_pagination(
    container_name: str,
    query: str,
    parameters: Optional[list] = None,
    page: int = 1,
    page_size: int = 10,
    partition_key: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], int]:
    return await cosmos_db_service.query_items_with_pagination(container_name, query, parameters, page, page_size)

async def query_items(
    container_name: str,
    query: str,
    parameters: Optional[list] = None,
    partition_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    return await cosmos_db_service.query_items(container_name, query, parameters, partition_key)


