"""
Logging utilities for FastAPI Azure Backend.

This module provides logging configuration and helpers.
"""

import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configure root logger
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger
logger = logging.getLogger("fastapi_azure_backend")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""
    
    async def dispatch(self, request: Request, call_next):
        """
        Process a request and log details.
        
        Args:
            request: The request to process
            call_next: The next middleware or route handler
            
        Returns:
            Response: The response from the next middleware or route handler
        """
        request_id = request.headers.get("X-Request-ID", "")
        start_time = datetime.utcnow()
        
        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path} "
            f"(ID: {request_id})"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"- Status: {response.status_code} - Duration: {duration_ms:.2f}ms "
                f"(ID: {request_id})"
            )
            
            return response
        except Exception as e:
            # Log exception
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"- Error: {str(e)} "
                f"(ID: {request_id})"
            )
            raise


def log_event(
    event_type: str,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an application event.
    
    Args:
        event_type: Type of event
        user_id: User ID
        resource_id: Resource ID
        details: Event details
    """
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type
    }
    
    if user_id:
        event["user_id"] = user_id
    
    if resource_id:
        event["resource_id"] = resource_id
    
    if details:
        event["details"] = details
    
    logger.info(f"EVENT: {json.dumps(event)}")


def configure_logger(log_level: str = "INFO") -> None:
    """
    Configure the logger.
    
    Args:
        log_level: Log level
    """
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    logger.setLevel(numeric_level)
