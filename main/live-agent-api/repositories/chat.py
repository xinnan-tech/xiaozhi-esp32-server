"""
Chat messages repository - Database operations for chat messages
"""
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import String, SmallInteger, TIMESTAMP, ForeignKey, Index, select, insert
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB

from infra.database import Base, utc_now


# ==================== ORM Model ====================

class ChatMessageModel(Base):
    __tablename__ = "chat_messages"

    # Primary key (internal)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Business key (external, ULID)
    message_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    
    # Foreign key to agents table (agent_id)
    agent_id: Mapped[str] = mapped_column(
        String(50), 
        ForeignKey("agents.agent_id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Message type: 1=user, 2=agent
    role: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    
    # JSONB content: [{"message_type": "text|audio|image|file", "message_content": "..."}]
    content: Mapped[List[dict]] = mapped_column(JSONB, nullable=False)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=utc_now, 
        nullable=False
    )

    __table_args__ = (
        Index('idx_chat_messages_message_id', 'message_id', unique=True),
        Index('idx_chat_messages_agent_id', 'agent_id'),
        Index('idx_chat_messages_agent_message_composite', 'agent_id', 'message_id'),
        Index('idx_chat_messages_content_gin', 'content', postgresql_using='gin'),
    )

    def __repr__(self):
        return f"<ChatMessageModel(id={self.id}, message_id={self.message_id}, agent_id={self.agent_id})>"


# ==================== Repository (CRUD Operations) ====================

class ChatMessage:
    """
    Chat Message Repository - Handles all database operations
    """
    
    @staticmethod
    async def create(
        db: AsyncSession,
        message_id: str,
        agent_id: str,
        role: int,
        content: List[dict]  # Already processed with S3 URLs
    ) -> ChatMessageModel:
        """
        Create new chat message
        
        Args:
            db: Database session
            message_id: Message ID (ULID)
            agent_id: Agent ID
            role: 1=user, 2=agent
            content: List of message parts with S3 URLs
            
        Returns:
            Created message model
        """
        message = ChatMessageModel(
            message_id=message_id,
            agent_id=agent_id,
            role=role,
            content=content
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    @staticmethod
    async def get_by_agent_cursor(
        db: AsyncSession,
        agent_id: str,
        cursor: Optional[str] = None,
        limit: int = 50
    ) -> Tuple[List[ChatMessageModel], Optional[str], bool]:
        """
        Get messages by agent_id using cursor-based pagination (chat style)
        
        Behavior:
        - First load (no cursor): Returns the latest messages (DESC order)
        - Scroll up (with cursor): Returns older messages before the cursor
        
        Args:
            db: Database session
            agent_id: Agent ID
            cursor: Message ID (ULID) to load messages before. If None, load latest messages
            limit: Number of messages to fetch
            
        Returns:
            Tuple of (messages, next_cursor, has_more)
        """
        # Build query with cursor
        query = select(ChatMessageModel).where(ChatMessageModel.agent_id == agent_id)
        
        # Apply cursor filter if provided - load messages BEFORE cursor (older messages)
        if cursor:
            query = query.where(ChatMessageModel.message_id < cursor)
        
        # Order by message_id DESC to get latest messages first
        # Fetch limit + 1 to check if there are more records
        query = query.order_by(ChatMessageModel.message_id.desc()).limit(limit + 1)
        
        result = await db.execute(query)
        messages: List[ChatMessageModel] = result.scalars().all()
        
        # Check if there are more messages
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]
        
        # Get next cursor (oldest message_id in current batch for loading earlier messages)
        next_cursor = None
        if has_more and messages:
            next_cursor = messages[-1].message_id
        
        return messages, next_cursor, has_more

    @staticmethod
    async def get_latest_by_agent(
        db: AsyncSession,
        agent_id: str
    ) -> Optional[ChatMessageModel]:
        """
        Get the latest message for a specific agent
        
        Args:
            db: Database session
            agent_id: Agent ID
            
        Returns:
            Latest message model or None
        """
        query = select(ChatMessageModel).where(
            ChatMessageModel.agent_id == agent_id
        ).order_by(ChatMessageModel.id.desc()).limit(1)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()

