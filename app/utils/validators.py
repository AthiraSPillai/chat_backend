"""
Validators and data sanitization utilities for FastAPI Azure Backend.

This module provides validation and sanitization functions for input data.
"""

import re
import unicodedata
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime
import uuid


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate an email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Simple regex for email validation
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, None


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a username.
    
    Args:
        username: Username to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 30:
        return False, "Username must be at most 30 characters long"
    
    if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
        return False, "Username can only contain letters, numbers, underscores, dots, and hyphens"
    
    return True, None


def sanitize_string(text: str) -> str:
    """
    Sanitize a string by removing control characters and normalizing whitespace.
    
    Args:
        text: String to sanitize
        
    Returns:
        str: Sanitized string
    """
    # Normalize unicode characters
    text = unicodedata.normalize('NFKC', text)
    
    # Remove control characters
    text = ''.join(ch for ch in text if unicodedata.category(ch)[0] != 'C')
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    return text


def validate_uuid(uuid_str: str) -> bool:
    """
    Validate a UUID string.
    
    Args:
        uuid_str: UUID string to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return str(uuid_obj) == uuid_str
    except (ValueError, AttributeError):
        return False


def validate_iso_date(date_str: str) -> bool:
    """
    Validate an ISO date string.
    
    Args:
        date_str: ISO date string to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return True
    except (ValueError, AttributeError):
        return False


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Validate a file extension.
    
    Args:
        filename: Filename to validate
        allowed_extensions: List of allowed extensions (without dots)
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not filename or '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions


def validate_content_type(content_type: str, allowed_types: List[str]) -> bool:
    """
    Validate a content type.
    
    Args:
        content_type: Content type to validate
        allowed_types: List of allowed content types
        
    Returns:
        bool: True if valid, False otherwise
    """
    return content_type in allowed_types


def validate_json_structure(data: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate a JSON structure.
    
    Args:
        data: JSON data to validate
        required_fields: List of required fields
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, None
