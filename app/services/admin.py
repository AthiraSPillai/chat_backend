"""
Admin service for FastAPI Azure Backend.

This module provides business logic for admin operations.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
import uuid

from api.admin.schema import UserCreate, UserUpdate, RoleCreate, RoleUpdate
from api.auth.schema import UserInDB, UserRole
from utils.password import get_password_hash, verify_password
logger = logging.getLogger(__name__)

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from api.admin.schema import UserCreate
from utils.password import get_password_hash
from integrations.azure_cosmos_db import cosmos_db_service  # Use singleton instance

logger = logging.getLogger(__name__)

class AdminService:
    """Admin service for user and role management."""

    def __init__(self,users_container=None, roles_container=None):

        """Initialize containers for users and roles."""
        self.users_container =  users_container
        self.roles_container =  roles_container

    async def create_user(self, user_data: UserCreate, creator_id: str) -> Dict[str, Any]:
        """
        Create a new user after verifying uniqueness of username and email.

        Args:
            user_data: UserCreate schema instance
            creator_id: ID of the user creating this user

        Returns:
            Created user dict without password hash

        Raises:
            ValueError if username or email already exists
        """
        if not self.users_container:
            await self.init_containers()

        # Check if username exists (partition key is username assumed here)
        query_username = "SELECT * FROM c WHERE c.username = @username"
        params_username = [{"name": "@username", "value": user_data.username}]

        existing_users = await cosmos_db_service.query_items(
            container_name="users",
            query=query_username,
            parameters=params_username,
            partition_key=user_data.username  # Use username as partition key if applicable
        )
        if existing_users:
            raise ValueError(f"Username '{user_data.username}' already exists")

        # Check if email exists (no partition key for email query)
        query_email = "SELECT * FROM c WHERE c.email = @email"
        params_email = [{"name": "@email", "value": user_data.email}]

        existing_emails = await cosmos_db_service.query_items(
            container_name="users",
            query=query_email,
            parameters=params_email,
            partition_key=None
        )
        if existing_emails:
            raise ValueError(f"Email '{user_data.email}' already exists")

        now = datetime.utcnow().isoformat()
        user_id = str(uuid.uuid4())

        user = {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": get_password_hash(user_data.password),
            "role": user_data.role,
            "is_admin": user_data.is_admin,
            "permissions": user_data.permissions or [],
            "created_at": now,
            "updated_at": now,
            "last_login": None,
            "active": True,
            "created_by": creator_id
        }

        # Create user item in Cosmos DB, partition key is username (adjust if your design differs)
        await self.users_container.create_item(body=user)

        # Remove password hash before returning
        user.pop("password_hash", None)

        return user

    async def list_users(
        self,
        skip: int,
        limit: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List users.
        
        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return
            filters: Filters to apply
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: List of users and total count
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
        query_parts.append("ORDER BY c.id")  # recommended to have ORDER BY for stable pagination
        query = " ".join(query_parts)
        query = query.replace("SELECT *", f"SELECT TOP @limit *")
        params.extend([
            {"name": "@skip", "value": skip},
            {"name": "@limit", "value": limit}
        ])
        
        
        # Execute query
        users = []
        async for item in self.users_container.query_items(
            query=query,
            parameters=params
        ):
            # Remove password hash from response
            item.pop("password_hash", None)
            users.append(item)
        
        # Count total users
        count_query_parts = ["SELECT VALUE COUNT(1) FROM c"]
        if len(query_parts) > 1 and "WHERE" in query_parts[1]:
            count_query_parts.append(query_parts[1])  # Add WHERE clause
        
        count_query = " ".join(count_query_parts)
        
        # Remove pagination params
        count_params = [p for p in params if p["name"] not in ("@skip", "@limit")]
        
        total = 0
        async for item in self.users_container.query_items(
            query=count_query,
            parameters=count_params
        ):
            total = item
            break
        
        return users, total
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user details.
        
        Args:
            user_id: User ID
            
        Returns:
            Optional[Dict[str, Any]]: User details or None if not found
        """
        try:
            user = await self.users_container.read_item(
                item=user_id,
                partition_key=user_id
            )
            
            # Remove password hash from response
            user.pop("password_hash", None)
            
            return user
        except Exception as e:
            logger.warning(f"Failed to get user {user_id}: {str(e)}")
            return None
    
    async def update_user(self, user_id: str, user_data: UserUpdate) -> Optional[Dict[str, Any]]:
        """
        Update user.
        
        Args:
            user_id: User ID
            user_data: User data
            
        Returns:
            Optional[Dict[str, Any]]: Updated user or None if not found
            
        Raises:
            ValueError: If the username or email already exists
        """
        try:
            # Get current user
            user = await self.users_container.read_item(
                item=user_id,
                partition_key=user_id
            )
            
            # Check if username exists
            if user_data.username and user_data.username != user["username"]:
                query = f"SELECT * FROM c WHERE c.username = @username"
                params = [{"name": "@username", "value": user_data.username}]
                
                existing_users = []
                async for item in self.users_container.query_items(
                    query=query,
                    parameters=params
                ):
                    existing_users.append(item)
                
                if existing_users:
                    raise ValueError(f"Username '{user_data.username}' already exists")
            
            # Check if email exists
            if user_data.email and user_data.email != user["email"]:
                query = f"SELECT * FROM c WHERE c.email = @email"
                params = [{"name": "@email", "value": user_data.email}]
                
                existing_emails = []
                async for item in self.users_container.query_items(
                    query=query,
                    parameters=params
                ):
                    existing_emails.append(item)
                
                if existing_emails:
                    raise ValueError(f"Email '{user_data.email}' already exists")
            
            # Update user
            if user_data.username:
                user["username"] = user_data.username
            
            if user_data.email:
                user["email"] = user_data.email
            
            if user_data.password:
                user["password_hash"] = get_password_hash(user_data.password)
            
            if user_data.role:
                user["role"] = user_data.role
            
            if user_data.is_admin is not None:
                user["is_admin"] = user_data.is_admin
            
            if user_data.permissions is not None:
                user["permissions"] = user_data.permissions
            
            if user_data.active is not None:
                user["active"] = user_data.active
            
            user["updated_at"] = datetime.utcnow().isoformat()
            
            # Save user
            updated_user = await self.users_container.replace_item(
                item=user_id,
                body=user
            )
            
            # Remove password hash from response
            updated_user.pop("password_hash", None)
            
            return updated_user
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            await self.users_container.delete_item(
                item=user_id,
                partition_key=user_id
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to delete user {user_id}: {str(e)}")
            return False
    
    async def update_user_activation(self, user_id: str, active: bool) -> Optional[Dict[str, Any]]:
        """
        Update user activation status.
        
        Args:
            user_id: User ID
            active: Active status
            
        Returns:
            Optional[Dict[str, Any]]: Updated user or None if not found
        """
        try:
            # Get current user
            user = await self.users_container.read_item(
                item=user_id,
                partition_key=user_id
            )
            
            # Update user
            user["active"] = active
            user["updated_at"] = datetime.utcnow().isoformat()
            
            # Save user
            updated_user = await self.users_container.replace_item(
                item=user_id,
                body=user
            )
            
            # Remove password hash from response
            updated_user.pop("password_hash", None)
            
            return updated_user
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    async def assign_role_to_user(self, user_id: str, role_id: str) -> Optional[Dict[str, Any]]:
        """
        Assign role to user.
        
        Args:
            user_id: User ID
            role_id: Role ID
            
        Returns:
            Optional[Dict[str, Any]]: Updated user or None if not found
            
        Raises:
            ValueError: If the role does not exist
        """
        try:
            # Check if role exists
            try:
                role = await self.roles_container.read_item(
                    item=role_id,
                    partition_key=role_id
                )
            except Exception as e:
                raise ValueError(f"Role {role_id} not found")
            
            # Get current user
            user = await self.users_container.read_item(
                item=user_id,
                partition_key=user_id
            )
            
            # Update user
            user["role"] = role["name"]
            user["permissions"] = role["permissions"]
            user["updated_at"] = datetime.utcnow().isoformat()
            
            # Save user
            updated_user = await self.users_container.replace_item(
                item=user_id,
                body=user
            )
            
            # Remove password hash from response
            updated_user.pop("password_hash", None)
            
            return updated_user
        except ValueError:
            raise
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    async def remove_role_from_user(self, user_id: str, role_id: str) -> Optional[Dict[str, Any]]:
        """
        Remove role from user.
        
        Args:
            user_id: User ID
            role_id: Role ID
            
        Returns:
            Optional[Dict[str, Any]]: Updated user or None if not found
        """
        try:
            # Get current user
            user = await self.users_container.read_item(
                item=user_id,
                partition_key=user_id
            )
            
            # Get role
            try:
                role = await self.roles_container.read_item(
                    item=role_id,
                    partition_key=role_id
                )
            except Exception as e:
                raise ValueError(f"Role {role_id} not found")
            
            # Check if user has this role
            if user["role"] != role["name"]:
                raise ValueError(f"User does not have role {role['name']}")
            
            # Update user
            user["role"] = UserRole.USER
            user["permissions"] = []
            user["updated_at"] = datetime.utcnow().isoformat()
            
            # Save user
            updated_user = await self.users_container.replace_item(
                item=user_id,
                body=user
            )
            
            # Remove password hash from response
            updated_user.pop("password_hash", None)
            
            return updated_user
        except ValueError:
            raise
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    async def create_role(self, role_data: RoleCreate, creator_id: str) -> Dict[str, Any]:
        """
        Create a new role.
        
        Args:
            role_data: Role data
            creator_id: Creator user ID
            
        Returns:
            Dict[str, Any]: Created role
            
        Raises:
            ValueError: If the role name already exists
        """
        # Check if role name exists
        query = f"SELECT * FROM c WHERE c.name = @name"
        params = [{"name": "@name", "value": role_data.name}]
        
        existing_roles = []
        async for item in self.roles_container.query_items(
            query=query,
            parameters=params
        ):
            existing_roles.append(item)
        
        if existing_roles:
            raise ValueError(f"Role name '{role_data.name}' already exists")
        
        # Create role
        now = datetime.utcnow().isoformat()
        role_id = str(uuid.uuid4())
        
        role = {
            "id": role_id,
            "name": role_data.name,
            "description": role_data.description,
            "permissions": role_data.permissions,
            "created_at": now,
            "updated_at": now,
            "created_by": creator_id
        }
        
        await self.roles_container.create_item(body=role)
        
        return role
    
    async def list_roles(
        self,
        skip: int,
        limit: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        List roles.
        
        Args:
            skip: Number of roles to skip
            limit: Maximum number of roles to return
            filters: Filters to apply
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: List of roles and total count
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
        roles = []
        async for item in self.roles_container.query_items(
            query=query,
            parameters=params
        ):
            roles.append(item)
        
        # Count total roles
        count_query_parts = ["SELECT VALUE COUNT(1) FROM c"]
        if len(query_parts) > 1 and "WHERE" in query_parts[1]:
            count_query_parts.append(query_parts[1])  # Add WHERE clause
        
        count_query = " ".join(count_query_parts)
        
        # Remove pagination params
        count_params = [p for p in params if p["name"] not in ("@skip", "@limit")]
        
        total = 0
        async for item in self.roles_container.query_items(
            query=count_query,
            parameters=count_params
        ):
            total = item
            break
        
        return roles, total
    
    async def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        """
        Get role details.
        
        Args:
            role_id: Role ID
            
        Returns:
            Optional[Dict[str, Any]]: Role details or None if not found
        """
        try:
            role = await self.roles_container.read_item(
                item=role_id,
                partition_key=role_id
            )
            
            return role
        except Exception as e:
            logger.warning(f"Failed to get role {role_id}: {str(e)}")
            return None
    
    async def update_role(self, role_id: str, role_data: RoleUpdate) -> Optional[Dict[str, Any]]:
        """
        Update role.
        
        Args:
            role_id: Role ID
            role_data: Role data
            
        Returns:
            Optional[Dict[str, Any]]: Updated role or None if not found
            
        Raises:
            ValueError: If the role name already exists
        """
        try:
            # Get current role
            role = await self.roles_container.read_item(
                item=role_id,
                partition_key=role_id
            )
            
            # Check if role name exists
            if role_data.name and role_data.name != role["name"]:
                query = f"SELECT * FROM c WHERE c.name = @name"
                params = [{"name": "@name", "value": role_data.name}]
                
                existing_roles = []
                async for item in self.roles_container.query_items(
                    query=query,
                    parameters=params
                ):
                    existing_roles.append(item)
                
                if existing_roles:
                    raise ValueError(f"Role name '{role_data.name}' already exists")
            
            # Update role
            if role_data.name:
                role["name"] = role_data.name
            
            if role_data.description:
                role["description"] = role_data.description
            
            if role_data.permissions is not None:
                role["permissions"] = role_data.permissions
            
            role["updated_at"] = datetime.utcnow().isoformat()
            
            # Save role
            updated_role = await self.roles_container.replace_item(
                item=role_id,
                body=role
            )
            
            return updated_role
        except Exception as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    async def delete_role(self, role_id: str) -> bool:
        """
        Delete role.
        
        Args:
            role_id: Role ID
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            await self.roles_container.delete_item(
                item=role_id,
                partition_key=role_id
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to delete role {role_id}: {str(e)}")
            return False
