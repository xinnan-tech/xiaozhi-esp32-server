"""
Chat service - Business logic for chat messages
"""
import base64
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from copy import deepcopy

from config.logger import setup_logging
from repositories.chat import ChatMessage as ChatMessageRepo
from repositories.file import FileRepository
from schemas.chat import ReportChatMessageRequest, ChatMessage as ChatMessageSchema, ClearChatResponse
from utils.ulid import ULID
from utils.exceptions import InternalServerException

TAG = __name__
logger = setup_logging(__name__)


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
        
        # Convert message_time from unix timestamp to datetime
        message_time = None
        if request.message_time:
            message_time = datetime.fromtimestamp(request.message_time, tz=timezone.utc)
        
        # Store in database
        chat_message = await ChatMessageRepo.create(
            db=db,
            message_id=message_id,
            agent_id=request.agent_id,
            role=request.role,
            content=content_dicts,
            message_time=message_time
        )
        
        return ChatMessageSchema(
            message_id=chat_message.message_id,
            agent_id=chat_message.agent_id,
            role=chat_message.role,
            content=chat_message.content,
            message_time=chat_message.message_time,
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
                message_time=message.message_time,
            ))
        
        return response_messages, next_cursor, has_more

    async def clear_agent_chat(
        self,
        db: AsyncSession,
        s3,
        agent_id: str
    ) -> ClearChatResponse:
        """
        Clear all chat data for an agent (messages and files)
        
        Note: Caller must verify agent ownership before calling this method
        
        Process:
        1. Delete all chat messages from database
        2. Delete all chat files from S3
        
        Args:
            db: Database session
            s3: S3 client
            agent_id: Agent ID
            
        Returns:
            ClearChatResponse with deletion counts
            
        Raises:
            InternalServerException: If database or S3 deletion fails
        """
        # Delete all messages from database
        try:
            deleted_messages = await ChatMessageRepo.delete_by_agent(db, agent_id)
        except Exception as e:
            logger.bind(tag=TAG).exception(f"Failed to delete chat messages for agent {agent_id}")
            raise InternalServerException(f"Failed to delete chat messages: {e}")
        
        # Delete all chat files from S3
        try:
            deleted_files = await FileRepository.delete_agent_chat_files(s3, agent_id)
        except Exception as e:
            logger.bind(tag=TAG).exception(f"Failed to delete chat files for agent {agent_id}")
            raise InternalServerException(f"Failed to delete chat files: {e}")
        
        return ClearChatResponse(
            agent_id=agent_id,
            deleted_messages=deleted_messages,
            deleted_files=deleted_files
        )


# Global singleton instance
chat_service = ChatService()
