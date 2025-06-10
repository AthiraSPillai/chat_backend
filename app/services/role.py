from azure.cosmos.exceptions import CosmosResourceNotFoundError
from integrations.azure_cosmos_db import cosmos_db_service
from api.admin.role_schema import RoleCreate, RoleUpdate, RoleInDB
import uuid
from datetime import datetime
from typing import Optional, List

async def create_role(role_data: RoleCreate) -> RoleInDB:
    container = await cosmos_db_service.get_container("roles")
    new_role = RoleInDB(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        **role_data.model_dump()
    )
    await container.create_item(body=new_role.model_dump())
    return new_role

async def get_role_by_id(role_id: str) -> Optional[RoleInDB]:
    container = await cosmos_db_service.get_container("roles")
    try:
        role = await container.read_item(item=role_id, partition_key=role_id)
        return RoleInDB(**role)
    except CosmosResourceNotFoundError:
        return None

async def get_all_roles() -> List[RoleInDB]:
    container = await cosmos_db_service.get_container("roles")
    roles = []
    async for item in container.query_items(
        query="SELECT * FROM c",
    ):
        roles.append(RoleInDB(**item))
    return roles

async def update_role(role_id: str, role_data: RoleUpdate) -> Optional[RoleInDB]:
    container = await cosmos_db_service.get_container("roles")
    existing_role = await get_role_by_id(role_id)
    if not existing_role:
        return None
    
    updated_data = role_data.model_dump(exclude_unset=True)
    for key, value in updated_data.items():
        setattr(existing_role, key, value)
    existing_role.updated_at = datetime.utcnow().isoformat()
    
    await container.replace_item(item=existing_role.id, body=existing_role.model_dump())
    return existing_role

async def delete_role(role_id: str) -> bool:
    container = await cosmos_db_service.get_container("roles")
    try:
        await container.delete_item(item=role_id, partition_key=role_id)
        return True
    except CosmosResourceNotFoundError:
        return False


