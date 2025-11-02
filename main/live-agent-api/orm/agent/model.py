"""
Agent ORM Model

Defines the Agent database table structure and basic data operations.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from orm.base import Base


class Agent(Base):
    """
    Agent database model
    
    Represents a voice assistant agent with its configuration.
    """
    __tablename__ = "agents"
    
    # Primary Key
    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="Agent unique ID (Snowflake ID)"
    )
    
    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Agent display name"
    )
    
    template: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="blank",
        comment="Agent template type (e.g., personal-assistant, blank)"
    )
    
    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
        comment="Agent language code (e.g., en, zh)"
    )
    
    # Agent Configuration
    first_message: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Agent's greeting message"
    )
    
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="System prompt for agent behavior"
    )
    
    wake_word: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PLAUD",
        comment="Wake word to activate agent"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        comment="Creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="Last update timestamp"
    )
    
    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, language={self.language})>"
    
    def to_dict(self) -> dict:
        """
        Convert model to dictionary
        
        Returns:
            Dictionary representation of the agent
        """
        return {
            "id": self.id,
            "name": self.name,
            "template": self.template,
            "language": self.language,
            "firstMessage": self.first_message,
            "systemPrompt": self.system_prompt,
            "wakeWord": self.wake_word,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

