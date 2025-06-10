import logging
from typing import Dict, Any, List, Optional
from io import BytesIO
import pandas as pd

from integrations.azure_blob import upload_blob
from integrations.azure_cosmos_db import get_container
from services.prompt import PromptService
from services.mapping import MappingService

logger = logging.getLogger(__name__)

class PromptImportService:
    """
    Service to handle importing prompts from Excel files.
    """

    def __init__(
        self,
        prompt_service: PromptService,
        mapping_service: MappingService,
        cosmos_client=None
    ):
        self.prompt_service = prompt_service
        self.mapping_service = mapping_service
        self.cosmos_client = cosmos_client
        self.prompts_container = None
        self.mappings_container = None

        if cosmos_client:
            self.prompts_container = cosmos_client.get_container_client("prompts")
            self.mappings_container = cosmos_client.get_container_client("mappings")

    async def process_excel_prompts(self, file_content: bytes, uploader_id: str):
        """
        Processes an Excel file containing prompt definitions, uploads the file to blob storage,
        and creates/updates prompts and their mappings in Cosmos DB.
        
        The Excel file is expected to have the following columns:
        - 'PromptName': Name of the prompt (required)
        - 'PromptDescription': Description of the prompt (optional)
        - 'PromptContent': The actual prompt text (required)
        - 'RoleName': Name of the role to map the prompt to (required)
        - 'TaskName': Name of the task to map the prompt to (required)
        - 'Metadata': JSON string of additional metadata (optional)
        """
        try:
            df = pd.read_excel(BytesIO(file_content))
        except Exception as e:
            raise ValueError(f"Error reading Excel file: {e}")

        required_columns = ['PromptName', 'PromptContent', 'RoleName', 'TaskName']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Missing required columns. Expected: {', '.join(required_columns)}")

        # Upload the Excel file to blob storage
        blob_path = f"excel_uploads/{uploader_id}/{pd.Timestamp.now().isoformat().replace(':', '-')}.xlsx"
        await upload_blob(
            container_name="excel-uploads", # Assuming a container named 'excel-uploads'
            blob_path=blob_path,
            content=file_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        logger.info(f"Excel file uploaded to blob: {blob_path}")

        for index, row in df.iterrows():
            prompt_name = str(row['PromptName']).strip()
            prompt_content = str(row['PromptContent']).strip()
            role_name = str(row['RoleName']).strip()
            task_name = str(row['TaskName']).strip()
            prompt_description = str(row['PromptDescription']).strip() if 'PromptDescription' in row and pd.notna(row['PromptDescription']) else None
            metadata_str = str(row['Metadata']).strip() if 'Metadata' in row and pd.notna(row['Metadata']) else "{}"

            if not prompt_name or not prompt_content or not role_name or not task_name:
                logger.warning(f"Skipping row {index + 2} due to missing required data.")
                continue

            try:
                metadata = json.loads(metadata_str)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in Metadata for row {index + 2}. Skipping metadata for this row.")
                metadata = {}

            # 1. Get or create Prompt
            prompt_id = await self._get_or_create_prompt(
                prompt_name, prompt_description, prompt_content, metadata, uploader_id
            )

            # 2. Get or create Role
            role_id = await self._get_or_create_role(role_name, uploader_id)

            # 3. Get or create Task
            task_id = await self._get_or_create_task(task_name, uploader_id)

            # 4. Create or update Mapping
            await self._create_or_update_mapping(role_id, task_id, prompt_id, uploader_id)

    async def _get_or_create_prompt(self, name: str, description: Optional[str], content: str, metadata: Dict[str, Any], creator_id: str) -> str:
        # Check if prompt exists
        query = f"SELECT * FROM c WHERE c.name = @name"
        params = [{"name": "@name", "value": name}]
        existing_prompts = [item async for item in self.prompts_container.query_items(query=query, parameters=params)]

        if existing_prompts:
            prompt = existing_prompts[0]
            # Optionally update content if different, creating a new version
            if prompt['content_preview'] != self.prompt_service._get_content_preview(content):
                updated_prompt = await self.prompt_service.update_prompt_content(prompt['id'], content, create_new_version=True)
                return updated_prompt['id']
            return prompt['id']
        else:
            # Create new prompt
            prompt_data = {
                "name": name,
                "description": description,
                "content": content,
                "metadata": metadata
            }
            created_prompt = await self.prompt_service.create_prompt(PromptCreate(**prompt_data), creator_id)
            return created_prompt['id']

    async def _get_or_create_role(self, name: str, creator_id: str) -> str:
        # Check if role exists
        roles_container = self.cosmos_client.get_container_client("roles")
        query = f"SELECT * FROM c WHERE c.name = @name"
        params = [{"name": "@name", "value": name}]
        existing_roles = [item async for item in roles_container.query_items(query=query, parameters=params)]

        if existing_roles:
            return existing_roles[0]['id']
        else:
            # Create new role
            role_data = {"name": name, "permissions": []}
            created_role = await self.cosmos_client.get_container_client("roles").create_item(body={
                "id": str(uuid.uuid4()),
                "name": name,
                "permissions": [],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "created_by": creator_id
            })
            return created_role['id']

    async def _get_or_create_task(self, name: str, creator_id: str) -> str:
        # Check if task exists
        tasks_container = self.cosmos_client.get_container_client("tasks")
        query = f"SELECT * FROM c WHERE c.name = @name"
        params = [{"name": "@name", "value": name}]
        existing_tasks = [item async for item in tasks_container.query_items(query=query, parameters=params)]

        if existing_tasks:
            return existing_tasks[0]['id']
        else:
            # Create new task
            task_data = {"name": name, "description": None}
            created_task = await self.cosmos_client.get_container_client("tasks").create_item(body={
                "id": str(uuid.uuid4()),
                "name": name,
                "description": None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "created_by": creator_id
            })
            return created_task['id']

    async def _create_or_update_mapping(self, role_id: str, task_id: str, prompt_id: str, creator_id: str):
        # Check if mapping exists
        query = f"SELECT * FROM c WHERE c.role_id = @role_id AND c.task_id = @task_id"
        params = [
            {"name": "@role_id", "value": role_id},
            {"name": "@task_id", "value": task_id}
        ]
        existing_mappings = [item async for item in self.mappings_container.query_items(query=query, parameters=params)]

        if existing_mappings:
            mapping = existing_mappings[0]
            if mapping['prompt_id'] != prompt_id:
                # Update existing mapping
                mapping['prompt_id'] = prompt_id
                mapping['updated_at'] = datetime.utcnow().isoformat()
                await self.mappings_container.replace_item(item=mapping['id'], body=mapping)
                logger.info(f"Updated mapping for role {role_id} and task {task_id} to prompt {prompt_id}")
        else:
            # Create new mapping
            mapping_data = {
                "role_id": role_id,
                "task_id": task_id,
                "prompt_id": prompt_id
            }
            await self.mapping_service.create_mapping(MappingCreate(**mapping_data), creator_id)
            logger.info(f"Created new mapping for role {role_id}, task {task_id}, and prompt {prompt_id}")


