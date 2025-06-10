"""
Mapping service for FastAPI Azure Backend.

This module provides business logic for role-task-prompt mapping management.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import uuid

from api.admin.schema import MappingCreate, MappingUpdate

logger = logging.getLogger(__name__)


class MappingService:
    """Mapping service for role-task-prompt mapping management."""
    
    def __init__(self, cosmos_client=None):
        """
        Initialize the mapping service.
        
        Args:
            cosmos_client: Cosmos DB client
        """
        self.cosmos_client = cosmos_client
        self.mappings_container = None
        self.roles_container = None
        self.tasks_container = None
        self.prompts_container = None
        
        if cosmos_client:
            self.mappings_container = cosmos_client.get_container_client("mappings")
            self.roles_container = cosmos_client.get_container_client("roles")
            self.tasks_container = cosmos_client.get_container_client("tasks")
            self.prompts_container = cosmos_client.get_container_client("prompts")
    
    async def create_mapping(self, mapping_data: MappingCreate, creator_id: str) -> Dict[str, Any]:
        """
        Create a new mapping.
        
        Args:
            mapping_data: Mapping data
            creator_id: Creator user ID
            
        Returns:
            Dict[str, Any]: Created mapping
            
        Raises:
            ValueError: If the role, task, or prompt does not exist, or if a mapping already exists
        """
        # Validate role
        try:
            role = await self.roles_container.read_item(
                item=mapping_data.role_id,
                partition_key=mapping_data.role_id
            )
        except Exception as e:
            raise ValueError(f"Role {mapping_data.role_id} not found")
        
        # Validate task
        try:
            task = await self.tasks_container.read_item(
                item=mapping_data.task_id,
                partition_key=mapping_data.task_id
            )
        except Exception as e:
            raise ValueError(f"Task {mapping_data.task_id} not found")
        
        # Validate prompt
        try:
            prompt = await self.prompts_container.read_item(
                item=mapping_data.prompt_id,
                partition_key=mapping_data.prompt_id
            )
        except Exception as e:
            raise ValueError(f"Prompt {mapping_data.prompt_id} not found")
        
        # Check if mapping already exists
        query = """
        SELECT * FROM c 
        WHERE c.role_id = @role_id 
        AND c.task_id = @task_id
        """
        params = [
            {"name": "@role_id", "value": mapping_data.role_id},
            {"name": "@task_id", "value": mapping_data.task_id}
        ]
        
        existing_mappings = []
        async for item in self.mappings_container.query_items(
            query=query,
            parameters=params
        ):
            existing_mappings.append(item)
        
        if existing_mappings:
            raise ValueError(f"Mapping for role {mapping_data.role_id} and task {mapping_data.task_id} already exists")
        
        # If this is a default mapping, unset any existing default mappings for this task
        if mapping_data.is_default:
            await self._unset_default_mappings(mapping_data.task_id)
        
        # Create mapping
        now = datetime.utcnow().isoformat()
        mapping_id = str(uuid.uuid4())
        
        mapping = {
            "id": mapping_id,
            "role_id": mapping_data.role_id,
            "task_id": mapping_data.task_id,
            "prompt_id": mapping_data.prompt_id,
            "parameters": mapping_data.parameters or {},
            "is_default": mapping_data.is_default,
            "created_at": now,
            "updated_at": now,
            "created_by": creator_id
        }
        
        await self.mappings_container.create_item(body=mapping)
        
        return mapping
    
    async def list_mappings(
        self,
        skip: int,
        limit: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List mappings.
        
        Args:
            skip: Number of mappings to skip
            limit: Maximum number of mappings to return
            filters: Filters to apply
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: List of mappings and total count
        """
        filters = filters or {}
        
        # Build query
        query_parts = ["SELECT * FROM c"]
        params = []
        
        if filters:
            conditions = []
            param_index = 0
            
            for key, value in filters.items():
                param_name = f"@p{param_index}"
                conditions.append(f"c.{key} = {param_name}")
                params.append({"name": param_name, "value": value})
                param_index += 1
            
            if conditions:
                query_parts.append("WHERE " + " AND ".join(conditions))
        
        # Add pagination
        query_parts.append("OFFSET @skip LIMIT @limit")
        params.extend([
            {"name": "@skip", "value": skip},
            {"name": "@limit", "value": limit}
        ])
        
        query = " ".join(query_parts)
        
        # Execute query
        mappings = []
        async for item in self.mappings_container.query_items(
            query=query,
            parameters=params
        ):
            mappings.append(item)
        
        # Count total mappings
        count_query_parts = ["SELECT VALUE COUNT(1) FROM c"]
        if len(query_parts) > 1 and "WHERE" in query_parts[1]:
            count_query_parts.append(query_parts[1])  # Add WHERE clause
        
        count_query = " ".join(count_query_parts)
        
        # Remove pagination params
        count_params = [p for p in params if p["name"] not in ("@skip", "@limit")]
        
        total = 0
        async for item in self.mappings_container.query_items(
            query=count_query,
            parameters=count_params
        ):
            total = item
            break
        
        return mappings, total
    
    async def get_mapping(self, mapping_id: str) -> Optional[Dict[str, Any]]:
        """
        Get mapping details.
        
        Args:
            mapping_id: Mapping ID
            
        Returns:
            Optional[Dict[str, Any]]: Mapping details or None if not found
        """
        try:
            mapping = await self.mappings_container.read_item(
                item=mapping_id,
                partition_key=mapping_id
            )
            
            return mapping
        except Exception as e:
            logger.warning(f"Failed to get mapping {mapping_id}: {str(e)}")
            return None
    
    async def update_mapping(self, mapping_id: str, mapping_data: MappingUpdate) -> Optional[Dict[str, Any]]:
        """
        Update mapping.
        
        Args:
            mapping_id: Mapping ID
            mapping_data: Mapping data
            
        Returns:
            Optional[Dict[str, Any]]: Updated mapping or None if not found
            
        Raises:
            ValueError: If the role, task, or prompt does not exist
        """
        try:
            # Get current mapping
            mapping = await self.mappings_container.read_item(
                item=mapping_id,
                partition_key=mapping_id
            )
            
            # Validate role
            if mapping_data.role_id:
                try:
                    role = await self.roles_container.read_item(
                        item=mapping_data.role_id,
                        partition_key=mapping_data.role_id
                    )
                except Exception as e:
                    raise ValueError(f"Role {mapping_data.role_id} not found")
            
            # Validate task
            if mapping_data.task_id:
                try:
                    task = await self.tasks_container.read_item(
                        item=mapping_data.task_id,
                        partition_key=mapping_data.task_id
                    )
                except Exception as e:
                    raise ValueError(f"Task {mapping_data.task_id} not found")
            
            # Validate prompt
            if mapping_data.prompt_id:
                try:
                    prompt = await self.prompts_container.read_item(
                        item=mapping_data.prompt_id,
                        partition_key=mapping_data.prompt_id
                    )
                except Exception as e:
                    raise ValueError(f"Prompt {mapping_data.prompt_id} not found")
            
            # Check if mapping already exists
            if mapping_data.role_id or mapping_data.task_id:
                role_id = mapping_data.role_id or mapping["role_id"]
                task_id = mapping_data.task_id or mapping["task_id"]
                
                if role_id != mapping["role_id"] or task_id != mapping["task_id"]:
                    query = """
                    SELECT * FROM c 
                    WHERE c.role_id = @role_id 
                    AND c.task_id = @task_id
                    AND c.id != @id
                    """
                    params = [
                        {"name": "@role_id", "value": role_id},
                        {"name": "@task_id", "value": task_id},
                        {"name": "@id", "value": mapping_id}
                    ]
                    
                    existing_mappings = []
                    async for item in self.mappings_container.query_items(
                        query=query,
                        parameters=params
                    ):
                        existing_mappings.append(item)
                    
                    if existing_mappings:
                        raise ValueError(f"Mapping for role {role_id} and task {task_id} already exists")
            
            # If this is becoming a default mapping, unset any existing default mappings for this task
            if mapping_data.is_default and not mapping["is_default"]:
                task_id = mapping_data.task_id or mapping["task_id"]
                await self._unset_default_mappings(task_id)
            
            # Update mapping
            if mapping_data.role_id:
                mapping["role_id"] = mapping_data.role_id
            
            if mapping_data.task_id:
                mapping["task_id"] = mapping_data.task_id
            
            if mapping_data.prompt_id:
                mapping["prompt_id"] = mapping_data.prompt_id
            
            if mapping_data.parameters is not None:
                mapping["parameters"] = mapping_data.parameters
            
            if mapping_data.is_default is not None:
                mapping["is_default"] = mapping_data.is_default
            
            mapping["updated_at"] = datetime.utcnow().isoformat()
            
            # Save mapping
            updated_mapping = await self.mappings_container.replace_item(
                item=mapping_id,
                body=mapping
            )
            
            return updated_mapping
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    async def delete_mapping(self, mapping_id: str) -> bool:
        """
        Delete mapping.
        
        Args:
            mapping_id: Mapping ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            await self.mappings_container.delete_item(
                item=mapping_id,
                partition_key=mapping_id
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to delete mapping {mapping_id}: {str(e)}")
            return False
    
    async def get_mapping_for_role_task(self, role_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get mapping for role and task.
        
        Args:
            role_id: Role ID
            task_id: Task ID
            
        Returns:
            Optional[Dict[str, Any]]: Mapping or None if not found
        """
        # Try to find a specific mapping for this role and task
        query = """
        SELECT * FROM c 
        WHERE c.role_id = @role_id 
        AND c.task_id = @task_id
        """
        params = [
            {"name": "@role_id", "value": role_id},
            {"name": "@task_id", "value": task_id}
        ]
        
        mappings = []
        async for item in self.mappings_container.query_items(
            query=query,
            parameters=params
        ):
            mappings.append(item)
        
        if mappings:
            return mappings[0]
        
        # If no specific mapping found, try to find a default mapping for this task
        query = """
        SELECT * FROM c 
        WHERE c.task_id = @task_id
        AND c.is_default = true
        """
        params = [
            {"name": "@task_id", "value": task_id}
        ]
        
        default_mappings = []
        async for item in self.mappings_container.query_items(
            query=query,
            parameters=params
        ):
            default_mappings.append(item)
        
        if default_mappings:
            return default_mappings[0]
        
        return None
    
    async def _unset_default_mappings(self, task_id: str) -> None:
        """
        Unset default mappings for task.
        
        Args:
            task_id: Task ID
        """
        query = """
        SELECT * FROM c 
        WHERE c.task_id = @task_id
        AND c.is_default = true
        """
        params = [
            {"name": "@task_id", "value": task_id}
        ]
        
        default_mappings = []
        async for item in self.mappings_container.query_items(
            query=query,
            parameters=params
        ):
            default_mappings.append(item)
        
        for mapping in default_mappings:
            mapping["is_default"] = False
            mapping["updated_at"] = datetime.utcnow().isoformat()
            
            await self.mappings_container.replace_item(
                item=mapping["id"],
                body=mapping
            )
