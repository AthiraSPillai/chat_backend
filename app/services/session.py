from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from config import settings  # Ensure this includes COSMOS_DB_URL, KEY, DB_NAME
import asyncio


class SessionManager:
    def __init__(self, cosmos_url: str, cosmos_key: str, db_name: str, container_name: str):
        self.client = CosmosClient(cosmos_url, cosmos_key)
        self.db_name = db_name
        self.container_name = container_name
        self.db = None
        self.container = None
        self._init_lock = asyncio.Lock()

    async def _initialize(self):
        if not self.container:
            async with self._init_lock:
                if not self.container:
                    self.db = await self.client.create_database_if_not_exists(self.db_name)
                    self.container = await self.db.create_container_if_not_exists(
                        id=self.container_name,
                        partition_key=PartitionKey(path="/user_id"),
                        offer_throughput=400
                    )

    async def save_chat_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        await self._initialize()
        session_data.setdefault("id", str(uuid4()))
        session_data.setdefault("created_at", datetime.utcnow().isoformat())
        return await self.container.upsert_item(session_data)

    async def get_user_sessions(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        await self._initialize()
        query = f"SELECT * FROM c WHERE c.user_id = @user_id ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit"
        params = [
            {"name": "@user_id", "value": user_id},
            {"name": "@limit", "value": limit}
        ]
        result_iterable = self.container.query_items(query=query, parameters=params)
        return [item async for item in result_iterable]

    async def get_session_by_id(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        await self._initialize()
        try:
            return await self.container.read_item(item=session_id, partition_key=user_id)
        except Exception:
            return None

    async def update_session(self, session_id: str, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        await self._initialize()
        existing = await self.get_session_by_id(session_id, user_id)
        if not existing:
            raise ValueError("Session not found")
        existing.update(updates)
        return await self.container.upsert_item(existing)

    async def delete_session(self, session_id: str, user_id: str) -> None:
        await self._initialize()
        await self.container.delete_item(item=session_id, partition_key=user_id)

    async def log_activity(self, user_id: str, action: str, meta: Optional[Dict[str, Any]] = None) -> None:
        """
        For UI session container: track user activity like chat_create, file_upload, login etc.
        """
        await self._initialize()
        log_entry = {
            "id": str(uuid4()),
            "user_id": user_id,
            "action": action,
            "meta": meta or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.container.upsert_item(log_entry)
