from typing import Any, Optional
from pydantic import BaseModel


class APIResponse(BaseModel):
    """Unified API response format"""
    code: int
    message: str
    data: Optional[Any] = None


def success_response(data: Any = {}, message: str = "success") -> dict:
    """Create success response"""
    return {
        "code": 200,
        "message": message,
        "data": data
    }


def error_response(code: int, message: str) -> dict:
    """Create error response"""
    return {
        "code": code,
        "message": message,
        "data": None
    }

