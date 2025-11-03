"""
Agent Schemas

Pydantic models for Agent API request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AgentBase(BaseModel):
    """Base schema for Agent with common fields"""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Agent display name"
    )
    language: str = Field(
        default="en",
        max_length=10,
        description="Agent language code (e.g., en, zh)"
    )
    first_message: Optional[str] = Field(
        None,
        alias="firstMessage",
        description="Agent's greeting message"
    )
    system_prompt: Optional[str] = Field(
        None,
        alias="systemPrompt",
        description="System prompt for agent behavior"
    )
    wake_word: str = Field(
        default="PLAUD",
        alias="wakeWord",
        max_length=50,
        description="Wake word to activate agent"
    )
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "name": "My Assistant",
                "language": "en",
                "firstMessage": "Hello! How can I help you today?",
                "systemPrompt": "You are a helpful assistant.",
                "wakeWord": "PLAUD"
            }
        }
    }


class AgentCreate(AgentBase):
    """Schema for creating a new Agent"""
    
    template: str = Field(
        default="blank",
        max_length=100,
        description="Agent template type (blank, personal_assistant, learning_companion, health_wellness, hospital_assistant)"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean agent name"""
        v = v.strip()
        if not v:
            raise ValueError("Agent name cannot be empty")
        return v
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language code"""
        v = v.lower().strip()
        # Basic validation for common language codes
        if len(v) < 2 or len(v) > 10:
            raise ValueError("Invalid language code")
        return v


class AgentUpdate(BaseModel):
    """Schema for updating an Agent (all fields optional, name is immutable)"""
    
    language: Optional[str] = Field(
        None,
        max_length=10,
        description="Agent language code"
    )
    first_message: Optional[str] = Field(
        None,
        alias="firstMessage",
        description="Agent's greeting message"
    )
    system_prompt: Optional[str] = Field(
        None,
        alias="systemPrompt",
        description="System prompt for agent behavior"
    )
    wake_word: Optional[str] = Field(
        None,
        alias="wakeWord",
        max_length=50,
        description="Wake word to activate agent"
    )
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "language": "zh",
                "firstMessage": "你好！有什么可以帮助你的吗？",
                "systemPrompt": "You are a helpful Chinese assistant.",
                "wakeWord": "小助手"
            }
        }
    }
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        """Validate language code"""
        if v is not None:
            v = v.lower().strip()
            if len(v) < 2 or len(v) > 10:
                raise ValueError("Invalid language code")
        return v


class AgentDuplicate(BaseModel):
    """Schema for duplicating an Agent"""
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name for the duplicated agent"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Copy of My Agent"
            }
        }
    }


class AgentResponse(AgentBase):
    """Schema for Agent response"""
    
    id: str = Field(..., description="Agent unique ID")
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
                "name": "My Assistant",
                "language": "en",
                "firstMessage": "Hello! How can I help you today?",
                "systemPrompt": "You are a helpful assistant.",
                "wakeWord": "PLAUD",
                "createdAt": "2024-01-01T00:00:00",
                "updatedAt": "2024-01-01T00:00:00"
            }
        }
    }


class AgentListQuery(BaseModel):
    """Schema for Agent list query parameters (sorted by creation time desc)"""
    
    search: Optional[str] = Field(
        None,
        max_length=255,
        description="Search keyword"
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
    
    model_config = {
        "populate_by_name": True
    }


class GeneratePromptRequest(BaseModel):
    """Schema for generating system prompt"""
    
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Description of the agent's purpose and requirements"
    )
    current_prompt: Optional[str] = Field(
        None,
        alias="currentPrompt",
        max_length=10000,
        description="Existing system prompt to refine or build upon (optional)"
    )
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "description": "a customer support agent for PLAUD that handles technical questions",
                "currentPrompt": "You are a helpful assistant for PLAUD customers."
            }
        }
    }


class GeneratePromptResponse(BaseModel):
    """Schema for generated system prompt response"""
    
    system_prompt: str = Field(
        ...,
        alias="systemPrompt",
        description="Generated system prompt"
    )
    
    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "systemPrompt": "You are a professional customer support agent for PLAUD..."
            }
        }
    }

