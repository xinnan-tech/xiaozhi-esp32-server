from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, TIMESTAMP, ForeignKey, Index, select, delete
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database import Base, utc_now


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
        skip: int = 0,
        limit: int = 20
    ) -> List[AgentModel]:
        """Get all agents owned by a user"""
        result = await db.execute(
            select(AgentModel)
            .where(AgentModel.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .order_by(AgentModel.created_at.desc())
        )
        return result.scalars().all()

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

