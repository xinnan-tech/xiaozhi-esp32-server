from datetime import datetime, timezone
from typing import Optional, List, Tuple, Any
from sqlalchemy import String, Text, TIMESTAMP, ForeignKey, Index, select, delete, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database import Base, utc_now
from repositories.chat import ChatMessageModel


# ==================== ORM Model ====================

class AgentModel(Base):
    __tablename__ = "agents"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Agent unique identifier (external)
    agent_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    
    # Foreign key to user table (user_id)
    owner_id: Mapped[str] = mapped_column(
        String(50), 
        ForeignKey("user.user_id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Agent info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Agent configuration
    voice_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    voice_opening: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_closing: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=utc_now, 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=utc_now, 
        onupdate=utc_now, 
        nullable=False
    )

    __table_args__ = (
        Index('idx_agents_agent_id', 'agent_id', unique=True),
        Index('idx_agents_owner_id', 'owner_id'),
    )

    def __repr__(self):
        return f"<AgentModel(id={self.id}, agent_id={self.agent_id}>"


# ==================== Repository (CRUD Operations) ====================

class Agent:
    """
    Agent Repository - Handles all database operations
    """
    
    @staticmethod
    async def get_by_id(db: AsyncSession, agent_id: str) -> Optional[AgentModel]:
        """Get agent by agent_id"""
        result = await db.execute(select(AgentModel).where(AgentModel.agent_id == agent_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_agents_by_owner(
        db: AsyncSession,
        owner_id: str,
        cursor: Optional[str] = None,
        limit: int = 20
    ) -> Tuple[List[AgentModel], Optional[str], bool]:
        """
        Get agents owned by a user with cursor-based pagination
        
        Args:
            db: Database session
            owner_id: User ID
            cursor: ISO datetime string of last item's created_at
            limit: Number of items to return
            
        Returns:
            (agents, next_cursor, has_more)
        """
        query = select(AgentModel).where(AgentModel.owner_id == owner_id)
        
        # Apply cursor filter if provided
        if cursor:
            try:
                cursor_time = datetime.fromisoformat(cursor)
                # Get records created before cursor time
                query = query.where(AgentModel.created_at < cursor_time)
            except (ValueError, TypeError):
                # Invalid cursor, ignore and start from beginning
                pass
        
        # Order by created_at DESC, agent_id DESC for stable sorting
        # Fetch limit + 1 to check if there are more records
        query = query.order_by(
            AgentModel.created_at.desc(),
            AgentModel.agent_id.desc()
        ).limit(limit + 1)
        
        result = await db.execute(query)
        agents: List[AgentModel] = result.scalars().all()
        
        # Check if there are more records
        has_more = len(agents) > limit
        if has_more:
            agents = agents[:limit]
        
        # Generate next cursor from last item
        next_cursor = None
        if has_more and agents:
            next_cursor = agents[-1].created_at.isoformat()
        
        return agents, next_cursor, has_more

    @staticmethod
    async def create(
        db: AsyncSession,
        agent_id: str,
        owner_id: str,
        name: str,
        instruction: str,
        avatar_url: Optional[str] = None,
        description: Optional[str] = None,
        voice_id: Optional[str] = None,
        voice_opening: Optional[str] = None,
        voice_closing: Optional[str] = None
    ) -> AgentModel:
        """Create a new agent"""
        agent = AgentModel(
            agent_id=agent_id,
            owner_id=owner_id,
            name=name,
            avatar_url=avatar_url,
            description=description,
            voice_id=voice_id,
            instruction=instruction,
            voice_opening=voice_opening,
            voice_closing=voice_closing
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        return agent

    @staticmethod
    async def update(
        db: AsyncSession,
        agent_id: str,
        **kwargs
    ) -> Optional[AgentModel]:
        """Update agent"""
        agent = await Agent.get_by_id(db, agent_id)
        if not agent:
            return None
        
        for key, value in kwargs.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        
        await db.commit()
        await db.refresh(agent)
        return agent

    @staticmethod
    async def delete(db: AsyncSession, agent_id: str) -> bool:
        """Delete agent by agent_id"""
        result = await db.execute(
            delete(AgentModel).where(AgentModel.agent_id == agent_id)
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def get_agents_with_latest_message(
        db: AsyncSession,
        owner_id: str,
        cursor: Optional[str] = None,
        limit: int = 20
    ) -> Tuple[List[Tuple[Any, ...]], Optional[str], bool]:
        """
        Get agents with their latest message, ordered by latest activity time
        
        Args:
            db: Database session
            owner_id: User ID
            cursor: ISO datetime string of last item's sort_time
            limit: Number of items to return
            
        Returns:
            Tuple of (rows, next_cursor, has_more)
            Each row contains: (AgentModel, latest_message_id, latest_message_role, 
                               latest_message_content, latest_message_time, sort_time)
        """
        # Subquery: get latest message per agent using DISTINCT ON
        # Use message_time for ordering (when message actually occurred)
        latest_msg_subq = (
            select(
                ChatMessageModel.agent_id,
                ChatMessageModel.message_id,
                ChatMessageModel.role,
                ChatMessageModel.content,
                ChatMessageModel.message_time.label('message_time')
            )
            .distinct(ChatMessageModel.agent_id)
            .order_by(ChatMessageModel.agent_id, ChatMessageModel.message_time.desc())
            .subquery('latest_messages')
        )
        
        # Sort time: use message time if available, otherwise agent created_at
        sort_time_expr = func.coalesce(
            latest_msg_subq.c.message_time, 
            AgentModel.created_at
        )
        
        sort_time = sort_time_expr.label('sort_time')
        
        # Main query: join agents with latest messages
        query = (
            select(
                AgentModel,
                latest_msg_subq.c.message_id.label('latest_message_id'),
                latest_msg_subq.c.role.label('latest_message_role'),
                latest_msg_subq.c.content.label('latest_message_content'),
                latest_msg_subq.c.message_time.label('latest_message_time'),
                sort_time
            )
            .outerjoin(latest_msg_subq, AgentModel.agent_id == latest_msg_subq.c.agent_id)
            .where(AgentModel.owner_id == owner_id)
        )
        
        # Apply cursor filter
        if cursor:
            try:
                # Handle URL encoding issues: '+' in URL becomes space
                cursor_str = cursor.replace(' ', '+')
                cursor_time = datetime.fromisoformat(cursor_str)
                # Ensure timezone-aware for proper comparison
                if cursor_time.tzinfo is None:
                    cursor_time = cursor_time.replace(tzinfo=timezone.utc)
                query = query.where(sort_time_expr < cursor_time)
            except (ValueError, TypeError):
                pass
        
        # Order by sort_time DESC, agent_id DESC for stable sorting
        query = query.order_by(sort_time.desc(), AgentModel.agent_id.desc()).limit(limit + 1)
        
        result = await db.execute(query)
        rows = result.all()
        
        # Check if there are more records
        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]
        
        # Generate next cursor from last item's sort_time (keep timezone info)
        next_cursor = None
        if has_more and rows:
            last_sort_time = rows[-1].sort_time
            if last_sort_time:
                next_cursor = last_sort_time.isoformat()
        
        return rows, next_cursor, has_more

