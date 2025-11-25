"""
Chat API endpoints - Message reporting and retrieval
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from infra import get_db, get_s3
from services.chat_service import chat_service
from schemas.chat import (
    ReportChatMessageRequest,
    ChatMessage,
    ChatMessagesListResponse
)

router = APIRouter()


@router.post("/report", response_model=ChatMessage)
async def report_message(
    request: ReportChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    s3 = Depends(get_s3)
):
    """
    Report a new chat message from xiaozhi-server
    
    Process:
    - Receives opus audio as base64
    - Uploads audio to S3 using FileRepository
    - Stores message with S3 URLs in database
    
    Request Body:
        - agent_id: Agent ID
        - chat_type: 1=user, 2=agent
        - content: List of message parts (text, image, file URLs)
        - audio_base64: Optional opus audio in base64 format
    
    Returns:
        Created message with S3 URLs
    """
    return await chat_service.report_message(db=db, s3=s3, request=request)


@router.get("/{agent_id}/messages", response_model=ChatMessagesListResponse)
async def get_agent_messages(
    agent_id: str,
    cursor: Optional[str] = Query(None, description="Message ID (ULID) cursor for pagination"),
    limit: int = Query(50, ge=1, le=100, description="Number of messages to fetch"),
    include_audio: bool = Query(False, description="Load audio base64 from S3"),
    db: AsyncSession = Depends(get_db),
    s3 = Depends(get_s3)
):
    """
    Get chat messages for an agent using cursor-based pagination (chat style)
    
    Features:
    - Returns latest messages first (DESC order, newest at top)
    - Scroll up to load older messages (typical chat UI behavior)
    - Cursor-based pagination for efficient real-time chat
    - Lazy audio loading (only when include_audio=True)
    
    Query Parameters:
        - cursor: Message ID (ULID) to load messages before. If None, load latest messages
        - limit: Number of messages to fetch (1-100, default 50)
        - include_audio: If True, downloads opus from S3 and returns as base64
    
    Returns:
        - messages: List of chat messages (newest first in each batch)
        - next_cursor: Message ID for loading older messages (None if no more history)
        - has_more: Whether there are more older messages
    
    Example:
        # First request - get latest 50 messages
        GET /chat/agent_123/messages?limit=50
        Response: {
            messages: [newest_msg, ..., oldest_msg_in_batch], 
            next_cursor: "01JD8X0000ABC",  # ID of oldest message in this batch
            has_more: true
        }
        
        # Scroll up - load older messages before cursor
        GET /chat/agent_123/messages?cursor=01JD8X0000ABC&limit=50
        Response: {
            messages: [newer_old_msg, ..., older_msg], 
            next_cursor: "01JD8W0000XYZ",
            has_more: true
        }
        
        # Continue until has_more is false (reached the beginning of chat history)
    """
    messages, next_cursor, has_more = await chat_service.get_agent_messages(
        db=db,
        s3=s3,
        agent_id=agent_id,
        cursor=cursor,
        limit=limit,
        include_audio=include_audio
    )
    
    return ChatMessagesListResponse(
        messages=messages,
        next_cursor=next_cursor,
        has_more=has_more
    )

