"""
DeviceAgentBinding Schemas

Pydantic models for DeviceAgentBinding API request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BindingOperation(BaseModel):
    """
    Schema for device-agent binding operations (bind/unbind)
    
    This schema represents the device-agent pair for all binding operations.
    """
    
    device_id: str = Field(
        ...,
        alias="deviceId",
        min_length=1,
        max_length=64,
        description="Device unique ID"
    )
    agent_id: str = Field(
        ...,
        alias="agentId",
        min_length=1,
        max_length=64,
        description="Agent unique ID"
    )
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "deviceId": "1234567890",
                "agentId": "0987654321"
            }
        }
    }


class BindingUpdate(BaseModel):
    """Schema for updating a DeviceAgentBinding"""
    
    agent_id: Optional[str] = Field(
        None,
        alias="agentId",
        min_length=1,
        max_length=64,
        description="Agent unique ID"
    )
    status: Optional[str] = Field(
        None,
        max_length=20,
        description="Binding status (bound, unbound)"
    )
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "agentId": "0987654321",
                "status": "bound"
            }
        }
    }


class BindingResponse(BaseModel):
    """Schema for DeviceAgentBinding response"""
    
    id: str = Field(..., description="Binding unique ID")
    device_id: str = Field(..., alias="deviceId", description="Device unique ID")
    agent_id: str = Field(..., alias="agentId", description="Agent unique ID")
    status: str = Field(..., description="Binding status")
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
                "id": "1122334455",
                "deviceId": "1234567890",
                "agentId": "0987654321",
                "status": "bound",
                "createdAt": "2024-01-01T00:00:00",
                "updatedAt": "2024-01-01T00:00:00"
            }
        }
    }


class BindingWithDetails(BindingResponse):
    """Schema for DeviceAgentBinding response with device and agent details"""
    
    device_name: Optional[str] = Field(None, alias="deviceName", description="Device name")
    agent_name: Optional[str] = Field(None, alias="agentName", description="Agent name")
    
    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "1122334455",
                "deviceId": "1234567890",
                "agentId": "0987654321",
                "status": "bound",
                "deviceName": "My PLAUD Device",
                "agentName": "My Assistant",
                "createdAt": "2024-01-01T00:00:00",
                "updatedAt": "2024-01-01T00:00:00"
            }
        }
    }


class BindingListQuery(BaseModel):
    """Schema for DeviceAgentBinding list query parameters"""
    
    device_id: Optional[str] = Field(
        None,
        alias="deviceId",
        description="Filter by device ID"
    )
    agent_id: Optional[str] = Field(
        None,
        alias="agentId",
        description="Filter by agent ID"
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

