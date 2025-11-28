from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ==================== Template Schemas ====================

class AgentTemplateResponse(BaseModel):
    """Agent template response"""
    template_id: str
    name: str
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    voice_id: Optional[str] = None
    instruction: Optional[str] = None
    voice_opening: Optional[str] = None
    voice_closing: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== Agent Response Schemas ====================

class AgentResponse(BaseModel):
    """Agent response"""
    agent_id: str
    name: str
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    voice_id: Optional[str] = None
    instruction: str
    voice_opening: Optional[str] = None
    voice_closing: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class AgentWithLatestMessage(BaseModel):
    """Agent with latest message for list view"""
    agent_id: str
    name: str
    avatar_url: Optional[str] = None
    last_activity_time: datetime  # 最近活动时间 (消息时间 or agent创建时间)
    latest_message_text: Optional[str] = None  # 最新消息的文本内容


class AgentListResponse(BaseModel):
    """Agent list response with cursor-based pagination"""
    agents: list[AgentWithLatestMessage]
    next_cursor: Optional[str] = None
    has_more: bool = False


class AgentConfigResponse(BaseModel):
    """Agent configuration for xiaozhi-server"""
    agent_id: str
    name: str
    voice_id: Optional[str] = None
    language: Optional[str] = None  # Voice language from Fish Audio
    instruction: str
    voice_opening: Optional[str] = None
    voice_closing: Optional[str] = None

