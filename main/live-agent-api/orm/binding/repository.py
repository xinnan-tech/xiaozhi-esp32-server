"""
DeviceAgentBinding Repository

Data access layer for DeviceAgentBinding entity.
Encapsulates all database operations for device-agent bindings.
"""

from typing import Optional
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from orm.binding.model import DeviceAgentBinding


class DeviceAgentBindingRepository:
    """Repository for DeviceAgentBinding data access operations"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session
        
        Args:
            db: SQLAlchemy async session
        """
        self.db = db
    
    async def find_by_id(self, binding_id: str) -> Optional[DeviceAgentBinding]:
        """
        Find binding by ID
        
        Args:
            binding_id: Binding unique ID
            
        Returns:
            DeviceAgentBinding instance or None if not found
        """
        stmt = select(DeviceAgentBinding).where(DeviceAgentBinding.id == binding_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def find_by_device_id(self, device_id: str) -> Optional[DeviceAgentBinding]:
        """
        Find binding by device ID
        
        Args:
            device_id: Device unique ID
            
        Returns:
            DeviceAgentBinding instance or None if not found
        """
        stmt = select(DeviceAgentBinding).where(DeviceAgentBinding.device_id == device_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def find_by_agent_id(self, agent_id: str) -> list[DeviceAgentBinding]:
        """
        Find all bindings for an agent
        
        Args:
            agent_id: Agent unique ID
            
        Returns:
            List of DeviceAgentBinding instances
        """
        stmt = select(DeviceAgentBinding).where(DeviceAgentBinding.agent_id == agent_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def find_by_device_and_agent(
        self,
        device_id: str,
        agent_id: str
    ) -> Optional[DeviceAgentBinding]:
        """
        Find binding by device ID and agent ID
        
        Args:
            device_id: Device unique ID
            agent_id: Agent unique ID
            
        Returns:
            DeviceAgentBinding instance or None if not found
        """
        stmt = select(DeviceAgentBinding).where(
            DeviceAgentBinding.device_id == device_id,
            DeviceAgentBinding.agent_id == agent_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def find_all(
        self,
        device_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[DeviceAgentBinding], int]:
        """
        Find all bindings with filtering, pagination and sorting
        
        Args:
            device_id: Filter by device ID
            agent_id: Filter by agent ID
            status: Filter by status
            page: Page number (starting from 1)
            page_size: Number of items per page
            sort_by: Field to sort by
            sort_order: Sort direction ('asc' or 'desc')
            
        Returns:
            Tuple of (bindings list, total count)
        """
        # Build base query
        stmt = select(DeviceAgentBinding)
        
        # Apply filters
        if device_id:
            stmt = stmt.where(DeviceAgentBinding.device_id == device_id)
        
        if agent_id:
            stmt = stmt.where(DeviceAgentBinding.agent_id == agent_id)
        
        if status:
            stmt = stmt.where(DeviceAgentBinding.status == status)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Apply sorting
        sort_column = getattr(DeviceAgentBinding, sort_by, DeviceAgentBinding.created_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())
        
        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        # Execute query
        result = await self.db.execute(stmt)
        bindings = list(result.scalars().all())
        
        return bindings, total
    
    async def save(self, binding: DeviceAgentBinding) -> DeviceAgentBinding:
        """
        Save or update binding
        
        Args:
            binding: DeviceAgentBinding instance to save
            
        Returns:
            Saved binding instance
        """
        self.db.add(binding)
        await self.db.flush()
        await self.db.refresh(binding)
        return binding
    
    async def delete(self, binding: DeviceAgentBinding) -> None:
        """
        Delete binding
        
        Args:
            binding: DeviceAgentBinding instance to delete
        """
        await self.db.delete(binding)
        await self.db.flush()
    
    async def exists(self, binding_id: str) -> bool:
        """
        Check if binding exists
        
        Args:
            binding_id: Binding unique ID
            
        Returns:
            True if binding exists, False otherwise
        """
        stmt = select(func.count()).where(DeviceAgentBinding.id == binding_id)
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count > 0
    
    async def device_has_binding(self, device_id: str) -> bool:
        """
        Check if device already has a binding
        
        Args:
            device_id: Device unique ID
            
        Returns:
            True if device has binding, False otherwise
        """
        stmt = select(func.count()).where(DeviceAgentBinding.device_id == device_id)
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count > 0

