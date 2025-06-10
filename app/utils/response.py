"""
Response models for FastAPI Azure Backend.

This module provides standardized response models for API endpoints.
"""

from typing import Generic, TypeVar, Optional, List, Any, Dict
from pydantic import BaseModel, Field

# Generic type for response data
T = TypeVar('T')


class SuccessResponse(BaseModel):
    """Standard success response model."""
    success: bool = True
    message: str
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully"
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""
    success: bool = False
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": "Resource not found",
                "detail": "The requested resource could not be found",
                "code": "NOT_FOUND"
            }
        }


class ValidationErrorItem(BaseModel):
    """Validation error item model."""
    loc: List[str] = Field(..., description="Location of the error")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Validation error response model."""
    success: bool = False
    error: str = "Validation error"
    detail: List[ValidationErrorItem]
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": "Validation error",
                "detail": [
                    {
                        "loc": ["body", "username"],
                        "msg": "field required",
                        "type": "value_error.missing"
                    }
                ]
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response model."""
    items: List[T]
    total: int
    page: int
    page_size: int
    pages: int
    
    class Config:
        schema_extra = {
            "example": {
                "items": [],
                "total": 0,
                "page": 1,
                "page_size": 10,
                "pages": 0
            }
        }


class DataResponse(BaseModel, Generic[T]):
    """Data response model."""
    success: bool = True
    data: T
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {}
            }
        }


def create_success_response(message: str) -> Dict[str, Any]:
    """
    Create a success response.
    
    Args:
        message: Success message
        
    Returns:
        Dict[str, Any]: Success response
    """
    return {
        "success": True,
        "message": message
    }


def create_error_response(error: str, detail: Optional[str] = None, code: Optional[str] = None) -> Dict[str, Any]:
    """
    Create an error response.
    
    Args:
        error: Error message
        detail: Error detail
        code: Error code
        
    Returns:
        Dict[str, Any]: Error response
    """
    response = {
        "success": False,
        "error": error
    }
    
    if detail:
        response["detail"] = detail
    
    if code:
        response["code"] = code
    
    return response


def create_data_response(data: Any) -> Dict[str, Any]:
    """
    Create a data response.
    
    Args:
        data: Response data
        
    Returns:
        Dict[str, Any]: Data response
    """
    return {
        "success": True,
        "data": data
    }
