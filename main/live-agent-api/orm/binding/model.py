"""
DeviceAgentBinding ORM Model

Defines the DeviceAgentBinding database table structure for linking devices and agents.
"""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from orm.base import Base


class DeviceAgentBinding(Base):
    """
    DeviceAgentBinding database model
    
    Represents the binding relationship between a device and an agent.
    Each device can only be bound to one agent at a time.
    """
    __tablename__ = "device_agent_bindings"
    __table_args__ = (
        UniqueConstraint('device_id', name='uq_device_id'),
    )
    
    # Primary Key
    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="Binding unique ID (ULID)"
    )
    
    # Foreign Keys
    device_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        comment="Device ID (FK)"
    )
    
    agent_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Agent ID (FK)"
    )
    
    # Binding Information
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="Binding status (active, inactive)"
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
        return f"<DeviceAgentBinding(id={self.id}, device_id={self.device_id}, agent_id={self.agent_id})>"
    
    def to_dict(self) -> dict:
        """
        Convert model to dictionary
        
        Returns:
            Dictionary representation of the binding
        """
        return {
            "id": self.id,
            "deviceId": self.device_id,
            "agentId": self.agent_id,
            "status": self.status,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

