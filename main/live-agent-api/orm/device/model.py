"""
Device ORM Model

Defines the Device database table structure and basic data operations.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from orm.base import Base


class Device(Base):
    """
    Device database model
    
    Represents a physical device that can be bound to agents.
    """
    __tablename__ = "devices"
    
    # Primary Key
    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="Device unique ID (ULID)"
    )
    
    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Device display name"
    )
    
    device_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Device hardware ID"
    )
    
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        comment="Device model (e.g., PLAUD NOTE)"
    )
    
    firmware_version: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        comment="Firmware version"
    )
    
    # Device Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        comment="Device status (active, inactive, offline)"
    )
    
    is_online: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether device is currently online"
    )
    
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        comment="Last seen timestamp"
    )
    
    # Additional Information
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Device description"
    )
    
    extra_data: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Additional metadata (JSON format)"
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
        return f"<Device(id={self.id}, name={self.name}, device_id={self.device_id})>"
    
    def to_dict(self) -> dict:
        """
        Convert model to dictionary
        
        Returns:
            Dictionary representation of the device
        """
        return {
            "id": self.id,
            "name": self.name,
            "deviceId": self.device_id,
            "model": self.model,
            "firmwareVersion": self.firmware_version,
            "status": self.status,
            "isOnline": self.is_online,
            "lastSeenAt": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "description": self.description,
            "extraData": self.extra_data,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

