"""
Prompt service for FastAPI Azure Backend.

This module provides business logic for prompt management.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import uuid

from api.admin.prompt_schema import PromptCreate, PromptUpdate
from integrations.azure_blob import upload_blob, download_blob, delete_blob
from integrations.azure_cosmos_db import get_container, query_items, read_item # Import necessary Cosmos DB functions
from config import settings  # Add this import (adjust path if needed)

logger = logging.getLogger(__name__)


class PromptService:
    """Prompt service for prompt management."""
    
    def __init__(self, cosmos_client=None):
        """
        Initialize the prompt service.
        
        Args:
            cosmos_client: Cosmos DB client
        """
        self.cosmos_client = cosmos_client
        self.prompts_container = None
        self.mappings_container = None # Add mappings container
        
        if cosmos_client:
            self.prompts_container = cosmos_client.get_container_client("prompts")
            self.mappings_container = cosmos_client.get_container_client("mappings") # Initialize mappings container
    
    async def create_prompt(self, prompt_data: PromptCreate, creator_id: str) -> Dict[str, Any]:
        """
        Create a new prompt.
        
        Args:
            prompt_data: Prompt data
            creator_id: Creator user ID
            
        Returns:
            Dict[str, Any]: Created prompt
            
        Raises:
            ValueError: If the prompt name already exists
        """
        # Check if prompt name exists
        query = f"SELECT * FROM c WHERE c.name = @name"
        params = [{"name": "@name", "value": prompt_data.name}]
        
        existing_prompts = []
        async for item in query_items(self.prompts_container, query, params):
            existing_prompts.append(item)
        
        if existing_prompts:
            raise ValueError(f"Prompt name \'{prompt_data.name}\' already exists")
        
        # Create prompt
        now = datetime.utcnow().isoformat()
        prompt_id = str(uuid.uuid4())
        version = 1
        
        # Create blob path
        blob_path = f"{prompt_id}/v{version}.txt"
        
        # Format prompt content
        formatted_content = self._format_prompt_content(
            prompt_data.name,
            version,
            prompt_data.description,
            prompt_data.metadata.get("parameters", []),
            prompt_data.content
        )
        
        # Upload to blob storage
        await upload_blob(
            container_name=settings.PROMPT_CONTAINER_NAME,
            blob_path=blob_path,
            content=formatted_content,
            content_type="text/plain"
        )
        
        # Create latest.txt symlink
        await upload_blob(
            container_name=settings.PROMPT_CONTAINER_NAME,
            blob_path=f"{prompt_id}/latest.txt",
            content=formatted_content,
            content_type="text/plain"
        )
        
        # Create prompt metadata in Cosmos DB
        prompt = {
            "id": prompt_id,
            "name": prompt_data.name,
            "description": prompt_data.description,
            "version": version,
            "blob_path": blob_path,
            "content_preview": self._get_content_preview(prompt_data.content),
            "metadata": prompt_data.metadata,
            "created_at": now,
            "updated_at": now,
            "created_by": creator_id
        }
        
        await self.prompts_container.create_item(body=prompt)
        
        return prompt
    
    async def list_prompts(
        self,
        skip: int,
        limit: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List prompts.
        
        Args:
            skip: Number of prompts to skip
            limit: Maximum number of prompts to return
            filters: Filters to apply
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: List of prompts and total count
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
                
                if key == "name":
                    conditions.append(f"CONTAINS(LOWER(c.name), LOWER({param_name}))")
                elif key == "tag":
                    conditions.append(f"ARRAY_CONTAINS(c.metadata.tags, {param_name})")
                else:
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
        prompts = []
        async for item in query_items(self.prompts_container, query, params):
            prompts.append(item)
        
        # Count total prompts
        count_query_parts = ["SELECT VALUE COUNT(1) FROM c"]
        if len(query_parts) > 1 and "WHERE" in query_parts[1]:
            count_query_parts.append(query_parts[1])  # Add WHERE clause
        
        count_query = " ".join(count_query_parts)
        
        # Remove pagination params
        count_params = [p for p in params if p["name"] not in ("@skip", "@limit")]
        
        total = 0
        async for item in query_items(self.prompts_container, count_query, count_params):
            total = item
            break
        
        return prompts, total
    
    async def get_prompt(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get prompt details.
        
        Args:
            prompt_id: Prompt ID
            
        Returns:
            Optional[Dict[str, Any]]: Prompt details or None if not found
        """
        try:
            prompt = await read_item(self.prompts_container, prompt_id, prompt_id)
            
            return prompt
        except Exception as e:
            logger.warning(f"Failed to get prompt {prompt_id}: {str(e)}")
            return None
    
    async def update_prompt(self, prompt_id: str, prompt_data: PromptUpdate) -> Optional[Dict[str, Any]]:
        """
        Update prompt.
        
        Args:
            prompt_id: Prompt ID
            prompt_data: Prompt data
            
        Returns:
            Optional[Dict[str, Any]]: Updated prompt or None if not found
            
        Raises:
            ValueError: If the prompt name already exists
        """
        try:
            # Get current prompt
            prompt = await read_item(self.prompts_container, prompt_id, prompt_id)
            
            # Check if prompt name exists
            if prompt_data.name and prompt_data.name != prompt["name"]:
                query = f"SELECT * FROM c WHERE c.name = @name"
                params = [{"name": "@name", "value": prompt_data.name}]
                
                existing_prompts = []
                async for item in query_items(self.prompts_container, query, params):
                    existing_prompts.append(item)
                
                if existing_prompts:
                    raise ValueError(f"Prompt name \'{prompt_data.name}\' already exists")
            
            # Update prompt
            if prompt_data.name:
                prompt["name"] = prompt_data.name
            
            if prompt_data.description:
                prompt["description"] = prompt_data.description
            
            if prompt_data.metadata is not None:
                prompt["metadata"] = prompt_data.metadata
            
            prompt["updated_at"] = datetime.utcnow().isoformat()
            
            # Save prompt
            updated_prompt = await self.prompts_container.replace_item(
                item=prompt_id,
                body=prompt
            )
            
            return updated_prompt
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    async def delete_prompt(self, prompt_id: str) -> bool:
        """
        Delete prompt.
        
        Args:
            prompt_id: Prompt ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            # Get current prompt
            prompt = await read_item(self.prompts_container, prompt_id, prompt_id)
            
            # Delete all blob versions
            try:
                # Get current version
                version = prompt["version"]
                
                # Delete all versions
                for v in range(1, version + 1):
                    await delete_blob(
                        container_name=settings.PROMPT_CONTAINER_NAME,
                        blob_path=f"{prompt_id}/v{v}.txt"
                    )
                
                # Delete latest.txt
                await delete_blob(
                    container_name=settings.PROMPT_CONTAINER_NAME,
                    blob_path=f"{prompt_id}/latest.txt"
                )
            except Exception as e:
                logger.warning(f"Failed to delete prompt blobs for {prompt_id}: {str(e)}")
            
            # Delete prompt metadata
            await self.prompts_container.delete_item(
                item=prompt_id,
                partition_key=prompt_id
            )
            
            return True
        except Exception as e:
            logger.warning(f"Failed to delete prompt {prompt_id}: {str(e)}")
            return False
    
    async def get_prompt_content(
        self,
        prompt_id: str,
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get prompt content.
        
        Args:
            prompt_id: Prompt ID
            version: Prompt version
            
        Returns:
            Optional[Dict[str, Any]]: Prompt content or None if not found
        """
        try:
            # Get prompt metadata
            prompt = await read_item(self.prompts_container, prompt_id, prompt_id)
            
            # Determine blob path
            if version is None:
                blob_path = f"{prompt_id}/latest.txt"
            else:
                if version < 1 or version > prompt["version"]:
                    raise ValueError(f"Invalid version: {version}")
                
                blob_path = f"{prompt_id}/v{version}.txt"
            
            # Get content from blob storage
            content_stream, _, _ = await download_blob(
                container_name=settings.PROMPT_CONTAINER_NAME,
                blob_path=blob_path
            )
            
            content = content_stream.read().decode("utf-8")
            
            return {
                "id": prompt_id,
                "name": prompt["name"],
                "version": version or prompt["version"],
                "content": content
            }
        except Exception as e:
            logger.warning(f"Failed to get prompt content {prompt_id}: {str(e)}")
            return None
    
    async def update_prompt_content(
        self,
        prompt_id: str,
        content: str,
        create_new_version: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Update prompt content.
        
        Args:
            prompt_id: Prompt ID
            content: Prompt content
            create_new_version: Whether to create a new version
            
        Returns:
            Optional[Dict[str, Any]]: Updated prompt or None if not found
        """
        try:
            # Get current prompt
            prompt = await read_item(self.prompts_container, prompt_id, prompt_id)
            
            # Determine version
            if create_new_version:
                version = prompt["version"] + 1
            else:
                version = prompt["version"]
            
            # Create blob path
            blob_path = f"{prompt_id}/v{version}.txt"
            
            # Format prompt content
            formatted_content = self._format_prompt_content(
                prompt["name"],
                version,
                prompt["description"],
                prompt["metadata"].get("parameters", []),
                content
            )
            
            # Upload to blob storage
            await upload_blob(
                container_name=settings.PROMPT_CONTAINER_NAME,
                blob_path=blob_path,
                content=formatted_content,
                content_type="text/plain"
            )
            
            # Update latest.txt
            await upload_blob(
                container_name=settings.PROMPT_CONTAINER_NAME,
                blob_path=f"{prompt_id}/latest.txt",
                content=formatted_content,
                content_type="text/plain"
            )
            
            # Update prompt metadata
            if create_new_version:
                prompt["version"] = version
                prompt["blob_path"] = blob_path
            
            prompt["content_preview"] = self._get_content_preview(content)
            prompt["updated_at"] = datetime.utcnow().isoformat()
            
            # Save prompt
            updated_prompt = await self.prompts_container.replace_item(
                item=prompt_id,
                body=prompt
            )
            
            return updated_prompt
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    def _format_prompt_content(
        self,
        name: str,
        version: int,
        description: str,
        parameters: List[str],
        content: str
    ) -> str:
        """
        Format prompt content.
        
        Args:
            name: Prompt name
            version: Prompt version
            description: Prompt description
            parameters: Prompt parameters
            content: Prompt content
            
        Returns:
            str: Formatted prompt content
        """
        header = [
            f"# System Prompt: {name}",
            f"# Version: {version}",
            f"# Description: {description}"
        ]
        
        if parameters:
            header.append(f"# Parameters: {', '.join(parameters)}")
        
        header.append("")
        header.append(content)
        
        return "\n".join(header)
    
    def _get_content_preview(self, content: str, max_length: int = 100) -> str:
        """
        Get content preview.
        
        Args:
            content: Content
            max_length: Maximum length
            
        Returns:
            str: Content preview
        """
        if len(content) <= max_length:
            return content
        
        return content[:max_length] + "..."

    async def get_prompt_by_role_and_task(
        self,
        role_id: str,
        task_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get prompt content based on role and task IDs.

        Args:
            role_id: Role ID
            task_id: Task ID

        Returns:
            Optional[Dict[str, Any]]: Prompt content or None if not found
        """
        try:
            # 1. Find the mapping for the given role and task
            query = (
                f"SELECT * FROM c WHERE c.role_id = @role_id AND c.task_id = @task_id"
            )
            params = [
                {"name": "@role_id", "value": role_id},
                {"name": "@task_id", "value": task_id},
            ]
            
            mapping = None
            async for item in query_items(self.mappings_container, query, params):
                mapping = item
                break

            if not mapping:
                logger.warning(f"No mapping found for role {role_id} and task {task_id}")
                return None

            prompt_id = mapping["prompt_id"]

            # 2. Get the prompt content using the prompt_id
            prompt_content = await self.get_prompt_content(prompt_id)
            return prompt_content

        except Exception as e:
            logger.error(f"Error getting prompt by role and task: {str(e)}")
            return None


