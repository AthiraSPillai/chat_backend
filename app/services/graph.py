"""
Graph service for FastAPI Azure Backend.

This module provides functions for managing graph data and queries.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from fastapi import BackgroundTasks

from services.session import create_item, read_item, replace_item, delete_item, query_items
from services.file import get_file_by_id, check_file_access
from integrations.graphrag import query_graph_service, build_graph_from_files
from api.graph.schema import GraphNodeType, GraphRelationType, GraphQueryType

logger = logging.getLogger(__name__)


async def query_graph(
    user_id: str,
    query: str,
    query_type: GraphQueryType = GraphQueryType.HYBRID,
    filters: Optional[Dict[str, Any]] = None,
    max_results: int = 10,
    include_nodes: bool = True,
    include_relations: bool = True,
    file_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Query the graph.
    
    Args:
        user_id: User ID
        query: Query text
        query_type: Query type
        filters: Query filters
        max_results: Maximum number of results
        include_nodes: Whether to include nodes in response
        include_relations: Whether to include relations in response
        file_ids: File IDs to query
        
    Returns:
        Dict[str, Any]: Query results
    """
    # Validate file access if file_ids provided
    if file_ids:
        for file_id in file_ids:
            file = await get_file_by_id(file_id)
            if not file:
                raise ValueError(f"File {file_id} not found")
            
            has_access = await check_file_access(file, user_id)
            if not has_access:
                raise ValueError(f"User {user_id} does not have access to file {file_id}")
    
    # Generate query ID
    query_id = str(uuid.uuid4())
    
    # Execute query
    start_time = datetime.utcnow()
    result = await query_graph_service(
        query=query,
        query_type=query_type,
        filters=filters or {},
        max_results=max_results,
        include_nodes=include_nodes,
        include_relations=include_relations,
        file_ids=file_ids,
        user_id=user_id
    )
    end_time = datetime.utcnow()
    execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
    
    # Format response
    return {
        "query_id": query_id,
        "nodes": result.get("nodes", []),
        "relations": result.get("relations", []),
        "relevance_scores": result.get("relevance_scores", {}),
        "execution_time_ms": execution_time_ms
    }


async def build_graph(
    user_id: str,
    file_ids: List[str],
    options: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Build a graph from files.
    
    Args:
        user_id: User ID
        file_ids: File IDs to build graph from
        options: Build options
        background_tasks: FastAPI background tasks
        
    Returns:
        Dict[str, Any]: Build job details
    """
    # Validate file access
    for file_id in file_ids:
        file = await get_file_by_id(file_id)
        if not file:
            raise ValueError(f"File {file_id} not found")
        
        has_access = await check_file_access(file, user_id)
        if not has_access:
            raise ValueError(f"User {user_id} does not have access to file {file_id}")
    
    # Generate build ID
    build_id = str(uuid.uuid4())
    
    # Start build in background
    background_tasks.add_task(
        build_graph_from_files,
        build_id=build_id,
        file_ids=file_ids,
        options=options,
        user_id=user_id
    )
    
    # Estimate completion time (5 minutes per file)
    estimated_completion = datetime.utcnow()
    for _ in file_ids:
        estimated_completion = estimated_completion.replace(minute=estimated_completion.minute + 5)
    
    # Format response
    return {
        "build_id": build_id,
        "status": "pending",
        "file_count": len(file_ids),
        "estimated_completion_time": estimated_completion
    }


async def get_graph_statistics(
    user_id: str,
    file_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get graph statistics.
    
    Args:
        user_id: User ID
        file_ids: Optional file IDs to filter by
        
    Returns:
        Dict[str, Any]: Graph statistics
    """
    # Validate file access if file_ids provided
    if file_ids:
        for file_id in file_ids:
            file = await get_file_by_id(file_id)
            if not file:
                raise ValueError(f"File {file_id} not found")
            
            has_access = await check_file_access(file, user_id)
            if not has_access:
                raise ValueError(f"User {user_id} does not have access to file {file_id}")
    
    # Query node counts
    node_query = "SELECT VALUE COUNT(1) FROM c WHERE c.user_id = @user_id"
    node_params = [{"name": "@user_id", "value": user_id}]
    
    if file_ids:
        file_conditions = []
        for i, file_id in enumerate(file_ids):
            file_param = f"@file{i}"
            file_conditions.append(f"c.source_id = {file_param}")
            node_params.append({"name": file_param, "value": file_id})
        
        node_query += f" AND ({' OR '.join(file_conditions)})"
    
    node_count_result = await query_items("graph_nodes", node_query, node_params)
    node_count = node_count_result[0] if node_count_result else 0
    
    # Query relation counts
    relation_query = "SELECT VALUE COUNT(1) FROM c WHERE c.user_id = @user_id"
    relation_params = [{"name": "@user_id", "value": user_id}]
    
    relation_count_result = await query_items("graph_relations", relation_query, relation_params)
    relation_count = relation_count_result[0] if relation_count_result else 0
    
    # Query node type counts
    node_type_counts = {}
    for node_type in GraphNodeType:
        type_query = f"SELECT VALUE COUNT(1) FROM c WHERE c.user_id = @user_id AND c.type = @type"
        type_params = [
            {"name": "@user_id", "value": user_id},
            {"name": "@type", "value": node_type}
        ]
        
        if file_ids:
            file_conditions = []
            for i, file_id in enumerate(file_ids):
                file_param = f"@file{i}"
                file_conditions.append(f"c.source_id = {file_param}")
                type_params.append({"name": file_param, "value": file_id})
            
            type_query += f" AND ({' OR '.join(file_conditions)})"
        
        type_count_result = await query_items("graph_nodes", type_query, type_params)
        node_type_counts[node_type] = type_count_result[0] if type_count_result else 0
    
    # Query relation type counts
    relation_type_counts = {}
    for relation_type in GraphRelationType:
        type_query = f"SELECT VALUE COUNT(1) FROM c WHERE c.user_id = @user_id AND c.type = @type"
        type_params = [
            {"name": "@user_id", "value": user_id},
            {"name": "@type", "value": relation_type}
        ]
        
        type_count_result = await query_items("graph_relations", type_query, type_params)
        relation_type_counts[relation_type] = type_count_result[0] if type_count_result else 0
    
    # Format response
    return {
        "node_count": node_count,
        "relation_count": relation_count,
        "node_type_counts": node_type_counts,
        "relation_type_counts": relation_type_counts,
        "file_count": len(file_ids) if file_ids else 0,
        "last_updated": datetime.utcnow()
    }


async def create_node(
    user_id: str,
    type: GraphNodeType,
    name: str,
    properties: Optional[Dict[str, Any]] = None,
    source_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a graph node.
    
    Args:
        user_id: User ID
        type: Node type
        name: Node name
        properties: Node properties
        source_id: Source ID (file, document, etc.)
        
    Returns:
        Dict[str, Any]: Created node
    """
    # Validate source_id if provided
    if source_id:
        file = await get_file_by_id(source_id)
        if not file:
            raise ValueError(f"File {source_id} not found")
        
        has_access = await check_file_access(file, user_id)
        if not has_access:
            raise ValueError(f"User {user_id} does not have access to file {source_id}")
    
    # Generate node ID
    node_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Create node entry
    node = {
        "id": node_id,
        "user_id": user_id,
        "type": type,
        "name": name,
        "properties": properties or {},
        "source_id": source_id,
        "created_at": now.isoformat()
    }
    
    # Save to database
    result = await create_item("graph_nodes", node)
    
    return result


async def get_node_by_id(node_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a graph node by ID.
    
    Args:
        node_id: Node ID
        user_id: User ID
        
    Returns:
        Optional[Dict[str, Any]]: Node if found and accessible, None otherwise
    """
    node = await read_item("graph_nodes", node_id, node_id)
    if not node:
        return None
    
    # Check ownership
    if node["user_id"] != user_id:
        return None
    
    return node


async def delete_node(node_id: str, user_id: str) -> bool:
    """
    Delete a graph node.
    
    Args:
        node_id: Node ID
        user_id: User ID
        
    Returns:
        bool: True if deleted, False if not found or not accessible
    """
    node = await get_node_by_id(node_id, user_id)
    if not node:
        return False
    
    # Delete node
    await delete_item("graph_nodes", node_id, node_id)
    
    # Delete relations involving this node
    # In a real implementation, this would use a bulk delete operation
    source_relations = await query_items(
        "graph_relations",
        "SELECT c.id FROM c WHERE c.source_id = @node_id",
        [{"name": "@node_id", "value": node_id}]
    )
    
    for relation in source_relations:
        await delete_item("graph_relations", relation["id"], node_id)
    
    target_relations = await query_items(
        "graph_relations",
        "SELECT c.id FROM c WHERE c.target_id = @node_id",
        [{"name": "@node_id", "value": node_id}]
    )
    
    for relation in target_relations:
        await delete_item("graph_relations", relation["id"], relation["source_id"])
    
    return True


async def create_relation(
    user_id: str,
    type: GraphRelationType,
    source_id: str,
    target_id: str,
    properties: Optional[Dict[str, Any]] = None,
    weight: float = 1.0
) -> Dict[str, Any]:
    """
    Create a graph relation.
    
    Args:
        user_id: User ID
        type: Relation type
        source_id: Source node ID
        target_id: Target node ID
        properties: Relation properties
        weight: Relation weight
        
    Returns:
        Dict[str, Any]: Created relation
    """
    # Validate source and target nodes
    source_node = await get_node_by_id(source_id, user_id)
    if not source_node:
        raise ValueError(f"Source node {source_id} not found or not accessible")
    
    target_node = await get_node_by_id(target_id, user_id)
    if not target_node:
        raise ValueError(f"Target node {target_id} not found or not accessible")
    
    # Generate relation ID
    relation_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Create relation entry
    relation = {
        "id": relation_id,
        "user_id": user_id,
        "type": type,
        "source_id": source_id,
        "target_id": target_id,
        "properties": properties or {},
        "weight": weight,
        "created_at": now.isoformat()
    }
    
    # Save to database
    result = await create_item("graph_relations", relation)
    
    return result


async def get_relation_by_id(relation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a graph relation by ID.
    
    Args:
        relation_id: Relation ID
        user_id: User ID
        
    Returns:
        Optional[Dict[str, Any]]: Relation if found and accessible, None otherwise
    """
    # In a real implementation, this would use a more efficient query
    relations = await query_items(
        "graph_relations",
        "SELECT * FROM c WHERE c.id = @relation_id AND c.user_id = @user_id",
        [
            {"name": "@relation_id", "value": relation_id},
            {"name": "@user_id", "value": user_id}
        ]
    )
    
    if not relations:
        return None
    
    return relations[0]


async def delete_relation(relation_id: str, user_id: str) -> bool:
    """
    Delete a graph relation.
    
    Args:
        relation_id: Relation ID
        user_id: User ID
        
    Returns:
        bool: True if deleted, False if not found or not accessible
    """
    relation = await get_relation_by_id(relation_id, user_id)
    if not relation:
        return False
    
    # Delete relation
    await delete_item("graph_relations", relation_id, relation["source_id"])
    
    return True


async def check_graph_access(file_ids: List[str], user_id: str) -> bool:
    """
    Check if a user has access to the graph for the specified files.
    
    Args:
        file_ids: File IDs to check access for
        user_id: User ID
        
    Returns:
        bool: True if the user has access, False otherwise
    """
    for file_id in file_ids:
        file = await get_file_by_id(file_id)
        if not file:
            return False
        
        has_access = await check_file_access(file, user_id)
        if not has_access:
            return False
    
    return True
