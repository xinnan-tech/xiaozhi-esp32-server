"""
Chat service - Business logic for chat messages
"""
import base64
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from copy import deepcopy

from repositories.chat import ChatMessage as ChatMessageRepo
from repositories.file import FileRepository
from schemas.chat import ReportChatMessageRequest, ChatMessage as ChatMessageSchema
from utils.ulid import ULID


class ChatService:
    """Service layer for chat message operations"""
    
    async def report_message(
        self,
        db: AsyncSession,
        s3,
        request: ReportChatMessageRequest
    ) -> ChatMessageSchema:
        """
        Handle message reporting from xiaozhi-server
        
        Process:
        1. Generate message_id (ULID)
        2. If audio exists: upload to S3 using message_id as filename
        3. Store message with S3 URLs in database
        
        Args:
            db: Database session
            s3: S3 client
            request: Chat message report request
            
        Returns:
            Created message response
        """
        # Generate unique message_id (ULID - time-ordered and unique)
        message_id = str(ULID())
        
        contents = deepcopy(request.content)
        
        # Handle audio upload if present
        for message in contents:
            if message.message_type != "audio":
                continue
            
            # Decode base64 audio to bytes (service layer handles data transformation)
            try:
                audio_bytes = base64.b64decode(message.message_content)
            except Exception as e:
                raise ValueError(f"Invalid base64 audio data: {e}")
            
            # Upload to S3 using FileRepository with message_id
            audio_url = await FileRepository.upload_chat_audio(
                s3,
                audio_bytes,
                request.agent_id,
                message_id=message_id,
                file_ext="opus"
            )
            
            # Replace audio content with S3 URL
            message.message_content = audio_url
        
        # Convert Pydantic models to dict for JSONB storage
        content_dicts = [msg.model_dump() for msg in contents]
        
        # Store in database
        chat_message = await ChatMessageRepo.create(
            db=db,
            message_id=message_id,
            agent_id=request.agent_id,
            role=request.role.value,
            content=content_dicts
        )
        
        return ChatMessageSchema(
            message_id=chat_message.message_id,
            agent_id=chat_message.agent_id,
            role=chat_message.role,
            content=chat_message.content,
            created_at=chat_message.created_at
        )

    async def get_agent_messages(
        self,
        db: AsyncSession,
        s3,
        agent_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
        include_audio: bool = False
    ) -> Tuple[List[ChatMessageSchema], Optional[str], bool]:
        """
        Retrieve messages for an agent using cursor-based pagination
        
        Process:
        1. Fetch messages from database using cursor (message_id based)
        2. Return messages with S3 URLs (lazy loading)
        
        Args:
            db: Database session
            s3: S3 client
            agent_id: Agent ID
            cursor: Message ID (ULID) cursor for pagination
            limit: Number of messages to fetch
            include_audio: Whether to load audio from S3 (not used yet)
            
        Returns:
            Tuple of (messages, next_cursor, has_more)
        """
        messages, next_cursor, has_more = await ChatMessageRepo.get_by_agent_cursor(
            db=db,
            agent_id=agent_id,
            cursor=cursor,
            limit=limit
        )
        response_messages: List[ChatMessageSchema] = []
        for message in messages:
            response_messages.append(ChatMessageSchema(
                message_id=message.message_id,
                agent_id=message.agent_id,
                role=message.role,
                content=message.content,
                created_at=message.created_at
            ))
        
        return response_messages, next_cursor, has_more


# Global singleton instance
chat_service = ChatService()
