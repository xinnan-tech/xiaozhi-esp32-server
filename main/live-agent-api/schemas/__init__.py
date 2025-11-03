"""
API Schemas

Pydantic models for request/response validation.
"""

# Agent schemas
from schemas.agent import (
    AgentBase,
    AgentCreate,
    AgentUpdate,
    AgentDuplicate,
    AgentResponse,
    AgentListQuery,
    GeneratePromptRequest,
    GeneratePromptResponse,
)

# Device schemas
from schemas.device import (
    DeviceBase,
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListQuery,
)

# Binding schemas
from schemas.binding import (
    BindingOperation,
    BindingUpdate,
    BindingResponse,
    BindingWithDetails,
    BindingListQuery,
)

__all__ = [
    # Agent schemas
    "AgentBase",
    "AgentCreate",
    "AgentUpdate",
    "AgentDuplicate",
    "AgentResponse",
    "AgentListQuery",
    "GeneratePromptRequest",
    "GeneratePromptResponse",
    
    # Device schemas
    "DeviceBase",
    "DeviceCreate",
    "DeviceUpdate",
    "DeviceResponse",
    "DeviceListQuery",
    
    # Binding schemas
    "BindingOperation",
    "BindingUpdate",
    "BindingResponse",
    "BindingWithDetails",
    "BindingListQuery",
]
