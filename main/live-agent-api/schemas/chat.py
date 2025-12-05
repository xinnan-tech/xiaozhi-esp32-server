"""
Chat messages schemas for API request/response validation
"""
from pydantic import BaseModel, Field, field_serializer
from typing import List, Literal, Optional
from datetime import datetime
import enum


class MessageBody(BaseModel):
    """Individual message content part (text, audio, image, or file)"""
    message_type: Literal["text", "audio", "image", "file"]
    message_content: str  # Text content or S3 URL

class ChatRole(enum.Enum):
    USER = 1
    AGENT = 2

class ReportChatMessageRequest(BaseModel):
    """Request schema for reporting a chat message from dialogue server"""
    agent_id: str = Field(..., max_length=50, description="Agent ID")
    role: int = Field(..., ge=1, le=2, description="1: user, 2: agent")
    content: List[MessageBody] = Field(..., description="Message content parts")
    message_time: int = Field(..., description="Unix timestamp when message actually occurred (for correct ordering)")


class ChatMessage(BaseModel):
    """Response schema for a single chat message"""
    message_id: str
    agent_id: str
    role: int  # 1: user, 2: agent
    content: List[MessageBody]
    message_time: datetime  # When message actually occurred (for ordering)
    
    @field_serializer('message_time')
    def serialize_message_time(self, value: datetime) -> str:
        """Serialize datetime to ISO format with timezone"""
        return value.isoformat()


class ChatMessagesListResponse(BaseModel):
    """Response schema for paginated chat messages (cursor-based, chat style)"""
    messages: List[ChatMessage]
    next_cursor: Optional[str] = Field(None, description="ISO timestamp to load older messages (pass as cursor for next request)")
    has_more: bool = Field(False, description="Whether there are more older messages available")

