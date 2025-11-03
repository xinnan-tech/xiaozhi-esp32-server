"""
Device Schemas

Pydantic models for Device API request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class DeviceBase(BaseModel):
    """Base schema for Device with common fields"""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Device display name"
    )
    device_id: str = Field(
        ...,
        alias="deviceId",
        min_length=1,
        max_length=255,
        description="Device hardware ID"
    )
    model: Optional[str] = Field(
        None,
        max_length=100,
        description="Device model (e.g., PLAUD NOTE)"
    )
    firmware_version: Optional[str] = Field(
        None,
        alias="firmwareVersion",
        max_length=50,
        description="Firmware version"
    )
    status: str = Field(
        default="active",
        max_length=20,
        description="Device status (active, inactive, offline)"
    )
    description: Optional[str] = Field(
        None,
        description="Device description"
    )
    extra_data: Optional[str] = Field(
        None,
        alias="extraData",
        description="Additional metadata (JSON format)"
    )
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "name": "My PLAUD Device",
                "deviceId": "PLAUD-12345678",
                "model": "PLAUD NOTE",
                "firmwareVersion": "1.0.0",
                "status": "active",
                "description": "My personal voice recorder"
            }
        }
    }


class DeviceCreate(DeviceBase):
    """Schema for creating a new Device"""
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean device name"""
        v = v.strip()
        if not v:
            raise ValueError("Device name cannot be empty")
        return v
    
    @field_validator('device_id')
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        """Validate and clean device ID"""
        v = v.strip()
        if not v:
            raise ValueError("Device ID cannot be empty")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value"""
        valid_statuses = ["active", "inactive", "offline"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class DeviceUpdate(BaseModel):
    """Schema for updating a Device (all fields optional)"""
    
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Device display name"
    )
    model: Optional[str] = Field(
        None,
        max_length=100,
        description="Device model"
    )
    firmware_version: Optional[str] = Field(
        None,
        alias="firmwareVersion",
        max_length=50,
        description="Firmware version"
    )
    status: Optional[str] = Field(
        None,
        max_length=20,
        description="Device status"
    )
    is_online: Optional[bool] = Field(
        None,
        alias="isOnline",
        description="Whether device is online"
    )
    description: Optional[str] = Field(
        None,
        description="Device description"
    )
    extra_data: Optional[str] = Field(
        None,
        alias="extraData",
        description="Additional metadata"
    )
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "name": "Updated Device Name",
                "status": "active",
                "isOnline": True,
                "firmwareVersion": "1.1.0"
            }
        }
    }
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean device name"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Device name cannot be empty")
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status value"""
        if v is not None:
            valid_statuses = ["active", "inactive", "offline"]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class DeviceResponse(BaseModel):
    """Schema for Device response"""
    
    id: str = Field(..., description="Device unique ID")
    name: str = Field(..., description="Device display name")
    device_id: str = Field(..., alias="deviceId", description="Device hardware ID")
    model: Optional[str] = Field(None, description="Device model")
    firmware_version: Optional[str] = Field(
        None,
        alias="firmwareVersion",
        description="Firmware version"
    )
    status: str = Field(..., description="Device status")
    is_online: bool = Field(..., alias="isOnline", description="Whether device is online")
    last_seen_at: Optional[datetime] = Field(
        None,
        alias="lastSeenAt",
        description="Last seen timestamp"
    )
    description: Optional[str] = Field(None, description="Device description")
    extra_data: Optional[str] = Field(
        None,
        alias="extraData",
        description="Additional metadata"
    )
    created_at: datetime = Field(
        ...,
        alias="createdAt",
        description="Creation timestamp"
    )
    updated_at: datetime = Field(
        ...,
        alias="updatedAt",
        description="Last update timestamp"
    )
    
    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "1234567890",
                "name": "My PLAUD Device",
                "deviceId": "PLAUD-12345678",
                "model": "PLAUD NOTE",
                "firmwareVersion": "1.0.0",
                "status": "active",
                "isOnline": True,
                "lastSeenAt": "2024-01-01T00:00:00",
                "description": "My personal voice recorder",
                "metadata": None,
                "createdAt": "2024-01-01T00:00:00",
                "updatedAt": "2024-01-01T00:00:00"
            }
        }
    }


class DeviceListQuery(BaseModel):
    """Schema for Device list query parameters"""
    
    search: Optional[str] = Field(
        None,
        max_length=255,
        description="Search keyword"
    )
    status: Optional[str] = Field(
        None,
        description="Filter by status"
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number"
    )
    page_size: int = Field(
        default=20,
        alias="pageSize",
        ge=1,
        le=100,
        description="Number of items per page"
    )
    sort_by: str = Field(
        default="createdAt",
        alias="sortBy",
        description="Sort field"
    )
    sort_order: str = Field(
        default="desc",
        alias="sortOrder",
        pattern="^(asc|desc)$",
        description="Sort order (asc or desc)"
    )
    
    model_config = {
        "populate_by_name": True
    }

