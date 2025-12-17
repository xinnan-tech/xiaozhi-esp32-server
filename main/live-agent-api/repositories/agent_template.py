from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, TIMESTAMP, Index, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database import Base, utc_now
from repositories.agent import AgentModel


# ==================== ORM Model ====================

class AgentTemplateModel(Base):
    __tablename__ = "agent_templates"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Template unique identifier (external)
    template_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    
    # Template info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Template configuration
    voice_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        Index('idx_agent_templates_template_id', 'template_id', unique=True),
    )

    def __repr__(self):
        return f"<AgentTemplateModel(id={self.id}, template_id={self.template_id}, name={self.name})>"


# ==================== Repository (CRUD Operations) ====================

class AgentTemplate:
    """
    AgentTemplate Repository - Handles all database operations
    """

    @staticmethod
    async def get_all(db: AsyncSession, limit: int = 10) -> List[AgentTemplateModel]:
        """
        Get all templates
        Args:
            db: AsyncSession
            limit: int
        Returns:
            List[AgentTemplateModel]
        """
        stmt = select(AgentTemplateModel).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create(
        db: AsyncSession,
        template_id: str,
        name: str,
        avatar_url: Optional[str] = None,
        description: Optional[str] = None,
        voice_id: Optional[str] = None,
        instruction: Optional[str] = None,
        voice_opening: Optional[str] = None,
        voice_closing: Optional[str] = None
    ) -> AgentTemplateModel:
        """Create a new agent template"""
        template = AgentTemplateModel(
            template_id=template_id,
            name=name,
            avatar_url=avatar_url,
            description=description,
            voice_id=voice_id,
            instruction=instruction,
            voice_opening=voice_opening,
            voice_closing=voice_closing
        )
        db.add(template)
        await db.commit()
        await db.refresh(template)
        return template

    @staticmethod
    async def get_available_for_user(
        db: AsyncSession, 
        user_id: str, 
        limit: int = 10
    ) -> List[AgentTemplateModel]:
        """
        Get templates that haven't been used by the user yet.
        
        Filters out templates where the user has already created an agent from.
        
        Args:
            db: AsyncSession
            user_id: User ID to check against
            limit: Maximum number of templates to return
            
        Returns:
            List of available templates for the user
        """
        # Subquery: get template_ids that user has already used
        used_template_ids = (
            select(AgentModel.template_id)
            .where(
                AgentModel.owner_id == user_id,
                AgentModel.template_id.isnot(None)
            )
            .scalar_subquery()
        )
        
        # Main query: get templates not in user's used list
        stmt = (
            select(AgentTemplateModel)
            .where(AgentTemplateModel.template_id.notin_(used_template_ids))
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()

