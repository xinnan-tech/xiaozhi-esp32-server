"""
Device Service

Business logic layer for Device operations.
Uses Repository pattern for data access.
"""

import logging
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from orm.device import Device, DeviceRepository
from schemas.device import DeviceCreate, DeviceUpdate, DeviceListQuery
from utils import id_generator


logger = logging.getLogger(__name__)


class DeviceService:
    """Service class for Device business logic"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize Device service
        
        Args:
            db: Database session
        """
        self.repo = DeviceRepository(db)
    
    async def get_device_list(
        self,
        query: DeviceListQuery
    ) -> tuple[list[Device], int]:
        """
        Get paginated list of devices with optional search and filtering
        
        Args:
            query: Query parameters for filtering and pagination
            
        Returns:
            Tuple of (devices list, total count)
        """
        devices, total = await self.repo.find_all(
            search=query.search,
            status=query.status,
            page=query.page,
            page_size=query.page_size,
        )
        
        logger.info(
            f"Retrieved {len(devices)} devices (page {query.page}, total {total})"
        )
        
        return devices, total
    
    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """
        Get device by ID
        
        Args:
            device_id: Device unique ID
            
        Returns:
            Device instance or None if not found
        """
        device = await self.repo.find_by_id(device_id)
        
        if device:
            logger.info(f"Retrieved device: {device_id}")
        else:
            logger.warning(f"Device not found: {device_id}")
        
        return device
    
    async def get_device_by_device_id(self, device_id: str) -> Optional[Device]:
        """
        Get device by hardware device ID
        
        Args:
            device_id: Device hardware ID
            
        Returns:
            Device instance or None if not found
        """
        device = await self.repo.find_by_device_id(device_id)
        
        if device:
            logger.info(f"Retrieved device by device_id: {device_id}")
        else:
            logger.warning(f"Device not found by device_id: {device_id}")
        
        return device
    
    async def create_device(self, device_data: DeviceCreate) -> Device:
        """
        Create a new device
        
        Args:
            device_data: Device creation data
            
        Returns:
            Created device instance
            
        Raises:
            ValueError: If device_id already exists
        """
        # Business logic: Check if device_id already exists
        if await self.repo.device_id_exists(device_data.device_id):
            raise ValueError(f"Device ID already exists: {device_data.device_id}")
        
        # Business logic: Generate unique ID
        device_id = id_generator.generate()
        
        # Business logic: Create device instance
        device = Device(
            id=device_id,
            name=device_data.name,
            device_id=device_data.device_id,
            device_model=device_data.device_model,
            firmware_version=device_data.firmware_version,
            status=device_data.status,
            description=device_data.description,
            meta_data=device_data.meta_data,
        )
        
        # Persist to database
        device = await self.repo.save(device)
        
        logger.info(f"Created device: {device_id} ({device.name})")
        
        return device
    
    async def update_device(
        self,
        device_id: str,
        device_data: DeviceUpdate
    ) -> Optional[Device]:
        """
        Update device configuration
        
        Args:
            device_id: Device unique ID
            device_data: Device update data
            
        Returns:
            Updated device instance or None if not found
        """
        # Get existing device
        device = await self.repo.find_by_id(device_id)
        if not device:
            return None
        
        # Business logic: Update fields
        update_data = device_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            # Convert camelCase to snake_case
            db_field = field.replace("firmwareVersion", "firmware_version")
            db_field = db_field.replace("metaData", "meta_data")
            
            if hasattr(device, db_field):
                setattr(device, db_field, value)
        
        # Business logic: Update last_seen_at if device comes online
        if "status" in update_data and update_data["status"] == "online":
            device.last_seen_at = datetime.now(timezone.utc)
        
        # Business logic: Update timestamp
        device.updated_at = datetime.now(timezone.utc)
        
        # Persist changes
        device = await self.repo.save(device)
        
        logger.info(f"Updated device: {device_id}")
        
        return device
    
    async def delete_device(self, device_id: str) -> bool:
        """
        Delete a device
        
        Args:
            device_id: Device unique ID
            
        Returns:
            True if deleted, False if not found
        """
        device = await self.repo.find_by_id(device_id)
        if not device:
            return False
        
        # TODO: Business logic - Check for binding relationships
        # For now, just delete the device
        # In production, should check if device has bindings and handle accordingly
        
        await self.repo.delete(device)
        
        logger.info(f"Deleted device: {device_id}")
        
        return True
    
    async def update_device_status(
        self,
        device_id: str,
        status: str
    ) -> Optional[Device]:
        """
        Update device connection status
        
        Args:
            device_id: Device unique ID
            status: Device connection status (online, offline)
            
        Returns:
            Updated device instance or None if not found
        """
        device = await self.repo.find_by_id(device_id)
        if not device:
            return None
        
        device.status = status
        device.last_seen_at = datetime.now(timezone.utc)
        device.updated_at = datetime.now(timezone.utc)
        
        device = await self.repo.save(device)
        
        logger.info(f"Updated device status: {device_id} (status={status})")
        
        return device


def get_device_service(db: AsyncSession) -> DeviceService:
    """
    Dependency function to get Device service
    
    Args:
        db: Database session
        
    Returns:
        DeviceService instance
    """
    return DeviceService(db)

