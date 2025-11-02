"""
API Response Wrapper

Provides standardized response format for all API endpoints.
"""

from typing import Any, Optional, TypeVar, Generic
from pydantic import BaseModel, Field


T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """
    Standard API response format
    
    Attributes:
        code: HTTP status code
        message: Response message
        data: Response data payload
    """
    code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Response message")
    data: Optional[T] = Field(None, description="Response data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 200,
                "message": "success",
                "data": {"id": "123", "name": "Example"}
            }
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Paginated list response format
    
    Attributes:
        total: Total number of items
        page: Current page number
        pageSize: Number of items per page
        items: List of items
    """
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    pageSize: int = Field(..., alias="pageSize", description="Number of items per page")
    items: list[T] = Field(..., description="List of items")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "total": 100,
                "page": 1,
                "pageSize": 20,
                "items": []
            }
        }


def success_response(
    data: Any = None,
    message: str = "success",
    code: int = 200
) -> ApiResponse:
    """
    Create a success response
    
    Args:
        data: Response data payload
        message: Success message
        code: HTTP status code
        
    Returns:
        Standardized success response
    """
    return ApiResponse(code=code, message=message, data=data)


def error_response(
    message: str,
    code: int = 400,
    data: Any = None
) -> ApiResponse:
    """
    Create an error response
    
    Args:
        message: Error message
        code: HTTP status code
        data: Additional error data
        
    Returns:
        Standardized error response
    """
    return ApiResponse(code=code, message=message, data=data)


def paginated_response(
    items: list[Any],
    total: int,
    page: int,
    page_size: int
) -> PaginatedResponse:
    """
    Create a paginated response
    
    Args:
        items: List of items
        total: Total number of items
        page: Current page number
        page_size: Number of items per page
        
    Returns:
        Paginated response
    """
    return PaginatedResponse(
        total=total,
        page=page,
        pageSize=page_size,
        items=items
    )

