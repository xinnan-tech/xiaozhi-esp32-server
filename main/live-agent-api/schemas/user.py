from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== Request Schemas ====================

class UserRegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)


class UserLoginRequest(BaseModel):
    """User login request"""
    username: str
    password: str


class PasswordUpdateRequest(BaseModel):
    """Password update request"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


# ==================== Response Schemas ====================

class UserInfo(BaseModel):
    """User information response"""
    user_id: str
    username: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response"""
    token: str
    expire: int  # seconds
    user: UserInfo


class TokenInfo(BaseModel):
    """Token information"""
    user_id: str
    username: str
    token: str
    expire_date: datetime

