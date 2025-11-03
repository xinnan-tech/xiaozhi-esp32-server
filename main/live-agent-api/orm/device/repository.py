"""
Device Repository

Data access layer for Device entity.
Encapsulates all database operations for Device.
"""

from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from orm.device.model import Device


class DeviceRepository:
    """Repository for Device data access operations"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session
        
        Args:
            db: SQLAlchemy async session
        """
        self.db = db
    
    async def find_by_id(self, device_id: str) -> Optional[Device]:
        """
        Find device by ID
        
        Args:
            device_id: Device unique ID
            
        Returns:
            Device instance or None if not found
        """
        stmt = select(Device).where(Device.id == device_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def find_by_device_id(self, device_id: str) -> Optional[Device]:
        """
        Find device by hardware device ID
        
        Args:
            device_id: Device hardware ID
            
        Returns:
            Device instance or None if not found
        """
        stmt = select(Device).where(Device.device_id == device_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def find_all(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Device], int]:
        """
        Find all devices with filtering and pagination (sorted by creation time desc)
        
        Args:
            search: Search keyword (searches in name and device_id)
            status: Filter by status
            page: Page number (starting from 1)
            page_size: Number of items per page
            
        Returns:
            Tuple of (devices list, total count)
        """
        # Build base query
        stmt = select(Device)
        
        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(Device.name.ilike(search_pattern))
        
        # Apply status filter
        if status:
            stmt = stmt.where(Device.status == status)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Apply sorting (fixed: created_at desc)
        stmt = stmt.order_by(Device.created_at.desc())
        
        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        # Execute query
        result = await self.db.execute(stmt)
        devices = list(result.scalars().all())
        
        return devices, total
    
    async def save(self, device: Device) -> Device:
        """
        Save or update device
        
        Args:
            device: Device instance to save
            
        Returns:
            Saved device instance
        """
        self.db.add(device)
        await self.db.flush()
        await self.db.refresh(device)
        return device
    
    async def delete(self, device: Device) -> None:
        """
        Delete device
        
        Args:
            device: Device instance to delete
        """
        await self.db.delete(device)
        await self.db.flush()
    
    async def exists(self, device_id: str) -> bool:
        """
        Check if device exists
        
        Args:
            device_id: Device unique ID
            
        Returns:
            True if device exists, False otherwise
        """
        stmt = select(func.count()).where(Device.id == device_id)
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count > 0
    
    async def device_id_exists(self, device_id: str) -> bool:
        """
        Check if hardware device ID exists
        
        Args:
            device_id: Device hardware ID
            
        Returns:
            True if device_id exists, False otherwise
        """
        stmt = select(func.count()).where(Device.device_id == device_id)
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count > 0

