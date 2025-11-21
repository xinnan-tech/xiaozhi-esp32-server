from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, TIMESTAMP, Index, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database import Base, utc_now


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

