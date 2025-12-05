from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, TIMESTAMP, ForeignKey, Index, select, delete, update
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database import Base, utc_now


# ==================== ORM Models ====================

class DeviceModel(Base):
    __tablename__ = "devices"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Device unique identifier (external)
    device_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    
    # Device serial number
    sn: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    
    # Owner user ID (null if unbound)
    owner_id: Mapped[str | None] = mapped_column(
        String(50), 
        ForeignKey("user.user_id", ondelete="SET NULL"), 
        nullable=True
    )
    
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
        Index('idx_devices_device_id', 'device_id', unique=True),
        Index('idx_devices_owner_id', 'owner_id'),
    )

    def __repr__(self):
        return f"<DeviceModel(id={self.id}, device_id={self.device_id})>"


class AgentDeviceBindingModel(Base):
    __tablename__ = "agent_device_bindings"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign keys
    device_id: Mapped[str] = mapped_column(
        String(50), 
        ForeignKey("devices.device_id", ondelete="CASCADE"), 
        nullable=False
    )
    agent_id: Mapped[str] = mapped_column(
        String(50), 
        ForeignKey("agents.agent_id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Whether this is the default agent for the device
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=utc_now, 
        nullable=False
    )

    __table_args__ = (
        Index('idx_bindings_device_id', 'device_id'),
        Index('idx_bindings_agent_id', 'agent_id'),
        Index('uk_device_agent', 'device_id', 'agent_id', unique=True),
    )

    def __repr__(self):
        return f"<AgentDeviceBindingModel(device_id={self.device_id}, agent_id={self.agent_id})>"


# ==================== Repository (CRUD Operations) ====================

class Device:
    """Device Repository - Handles all device database operations"""
    
    @staticmethod
    async def get_by_id(db: AsyncSession, device_id: str) -> Optional[DeviceModel]:
        """Get device by device_id"""
        result = await db.execute(select(DeviceModel).where(DeviceModel.device_id == device_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_owner(db: AsyncSession, owner_id: str) -> List[DeviceModel]:
        """Get all devices owned by a user"""
        result = await db.execute(
            select(DeviceModel)
            .where(DeviceModel.owner_id == owner_id)
            .order_by(DeviceModel.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def create(
        db: AsyncSession,
        device_id: str,
        owner_id: Optional[str] = None
    ) -> DeviceModel:
        """Create a new device"""
        device = DeviceModel(
            device_id=device_id,
            owner_id=owner_id
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
        return device

    @staticmethod
    async def update_owner(
        db: AsyncSession,
        device_id: str,
        owner_id: Optional[str]
    ) -> Optional[DeviceModel]:
        """Update device owner"""
        device = await Device.get_by_id(db, device_id)
        if not device:
            return None
        
        device.owner_id = owner_id
        await db.commit()
        await db.refresh(device)
        return device

    @staticmethod
    async def unbind(db: AsyncSession, device_id: str) -> bool:
        """Unbind device: clear owner_id and delete all agent bindings"""
        # Clear owner_id
        result = await db.execute(
            update(DeviceModel)
            .where(DeviceModel.device_id == device_id)
            .values(owner_id=None)
        )
        
        # Delete all agent bindings
        await db.execute(
            delete(AgentDeviceBindingModel)
            .where(AgentDeviceBindingModel.device_id == device_id)
        )
        
        await db.commit()
        return result.rowcount > 0


class AgentDeviceBinding:
    """Agent-Device Binding Repository"""
    
    @staticmethod
    async def get_bindings_by_device(
        db: AsyncSession, 
        device_id: str
    ) -> List[AgentDeviceBindingModel]:
        """Get all agent bindings for a device"""
        result = await db.execute(
            select(AgentDeviceBindingModel)
            .where(AgentDeviceBindingModel.device_id == device_id)
            .order_by(AgentDeviceBindingModel.is_default.desc(), AgentDeviceBindingModel.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_binding(
        db: AsyncSession, 
        device_id: str, 
        agent_id: str
    ) -> Optional[AgentDeviceBindingModel]:
        """Get specific binding"""
        result = await db.execute(
            select(AgentDeviceBindingModel)
            .where(
                AgentDeviceBindingModel.device_id == device_id,
                AgentDeviceBindingModel.agent_id == agent_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_default_binding(
        db: AsyncSession, 
        device_id: str
    ) -> Optional[AgentDeviceBindingModel]:
        """Get default agent binding for a device"""
        result = await db.execute(
            select(AgentDeviceBindingModel)
            .where(
                AgentDeviceBindingModel.device_id == device_id,
                AgentDeviceBindingModel.is_default == True
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        device_id: str,
        agent_id: str,
        is_default: bool = False
    ) -> AgentDeviceBindingModel:
        """Create a new binding"""
        # If setting as default, clear other defaults first
        if is_default:
            await db.execute(
                update(AgentDeviceBindingModel)
                .where(AgentDeviceBindingModel.device_id == device_id)
                .values(is_default=False)
            )
        
        binding = AgentDeviceBindingModel(
            device_id=device_id,
            agent_id=agent_id,
            is_default=is_default
        )
        db.add(binding)
        await db.commit()
        await db.refresh(binding)
        return binding

    @staticmethod
    async def set_default(
        db: AsyncSession,
        device_id: str,
        agent_id: str
    ) -> bool:
        """Set an agent as default for device"""
        # Clear all defaults for this device
        await db.execute(
            update(AgentDeviceBindingModel)
            .where(AgentDeviceBindingModel.device_id == device_id)
            .values(is_default=False)
        )
        
        # Set the specified agent as default
        result = await db.execute(
            update(AgentDeviceBindingModel)
            .where(
                AgentDeviceBindingModel.device_id == device_id,
                AgentDeviceBindingModel.agent_id == agent_id
            )
            .values(is_default=True)
        )
        
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def delete(db: AsyncSession, device_id: str, agent_id: str) -> bool:
        """Delete a binding"""
        result = await db.execute(
            delete(AgentDeviceBindingModel)
            .where(
                AgentDeviceBindingModel.device_id == device_id,
                AgentDeviceBindingModel.agent_id == agent_id
            )
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def delete_all_by_device(db: AsyncSession, device_id: str) -> int:
        """Delete all bindings for a device"""
        result = await db.execute(
            delete(AgentDeviceBindingModel)
            .where(AgentDeviceBindingModel.device_id == device_id)
        )
        await db.commit()
        return result.rowcount

