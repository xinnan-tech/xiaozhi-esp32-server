"""
Device ORM Model

Defines the Device database table structure and basic data operations.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
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
    
    device_model: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        comment="Device model name (e.g., PLAUD NOTE, ESP32-S3)"
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
        default="offline",
        comment="Device connection status (online, offline)"
    )
    
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        comment="Last seen timestamp"
    )
    
    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Device description"
    )
    
    meta_data: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Device metadata (JSON format)"
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
            "deviceModel": self.device_model,
            "firmwareVersion": self.firmware_version,
            "status": self.status,
            "lastSeenAt": self.last_seen_at.isoformat() if self.last_seen_at else None,
            "description": self.description,
            "metaData": self.meta_data,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

