from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ==================== Request Schemas ====================

class DeviceBindRequest(BaseModel):
    """Request to bind a device"""
    device_id: str = Field(..., description="Device unique identifier")


class DeviceAddAgentRequest(BaseModel):
    """Request to add an agent to device"""
    agent_id: str = Field(..., description="Agent ID to add")
    is_default: bool = Field(default=False, description="Set as default agent")


# ==================== Response Schemas ====================

class AgentBindingResponse(BaseModel):
    """Agent binding info"""
    agent_id: str
    is_default: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DeviceResponse(BaseModel):
    """Device response"""
    device_id: str
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class DeviceWithBindingsResponse(BaseModel):
    """Device with agent bindings"""
    device_id: str
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    bindings: List[AgentBindingResponse] = []


class DeviceListResponse(BaseModel):
    """Device list response"""
    devices: List[DeviceWithBindingsResponse]

