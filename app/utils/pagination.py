"""
Pagination utilities for FastAPI Azure Backend.

This module provides pagination helpers for API endpoints.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class PaginationParams:
    """Pagination parameters."""
    page: int = 1
    page_size: int = 10
    
    def get_skip(self) -> int:
        """
        Get the number of items to skip.
        
        Returns:
            int: Number of items to skip
        """
        return (self.page - 1) * self.page_size
    
    def get_limit(self) -> int:
        """
        Get the number of items to return.
        
        Returns:
            int: Number of items to return
        """
        return self.page_size
    
    def get_pagination_info(self, total_items: int) -> dict:
        """
        Get pagination information.
        
        Args:
            total_items: Total number of items
            
        Returns:
            dict: Pagination information
        """
        total_pages = (total_items + self.page_size - 1) // self.page_size if total_items > 0 else 0
        
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total": total_items,
            "pages": total_pages,
            "has_next": self.page < total_pages,
            "has_prev": self.page > 1
        }


def get_page_params(page: Optional[int] = 1, page_size: Optional[int] = 10) -> PaginationParams:
    """
    Get pagination parameters.
    
    Args:
        page: Page number (1-based)
        page_size: Page size
        
    Returns:
        PaginationParams: Pagination parameters
    """
    # Ensure valid values
    page = max(1, page or 1)
    page_size = max(1, min(100, page_size or 10))
    
    return PaginationParams(page=page, page_size=page_size)
