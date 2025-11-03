"""
DeviceAgentBinding Service

Business logic layer for DeviceAgentBinding operations.
Uses Repository pattern for data access.
"""

import logging
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from orm.binding import DeviceAgentBinding, DeviceAgentBindingRepository
from orm.device import DeviceRepository
from orm.agent import AgentRepository
from schemas.binding import BindingOperation, BindingUpdate, BindingListQuery
from utils import id_generator


logger = logging.getLogger(__name__)


class BindingService:
    """Service class for DeviceAgentBinding business logic"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize Binding service
        
        Args:
            db: Database session
        """
        self.repo = DeviceAgentBindingRepository(db)
        self.device_repo = DeviceRepository(db)
        self.agent_repo = AgentRepository(db)
    
    async def get_binding_list(
        self,
        query: BindingListQuery
    ) -> tuple[list[DeviceAgentBinding], int]:
        """
        Get paginated list of bindings with optional filtering
        
        Args:
            query: Query parameters for filtering and pagination
            
        Returns:
            Tuple of (bindings list, total count)
        """
        bindings, total = await self.repo.find_all(
            device_id=query.device_id,
            agent_id=query.agent_id,
            status=query.status,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        
        logger.info(
            f"Retrieved {len(bindings)} bindings (page {query.page}, total {total})"
        )
        
        return bindings, total
    
    async def get_binding_by_id(self, binding_id: str) -> Optional[DeviceAgentBinding]:
        """
        Get binding by ID
        
        Args:
            binding_id: Binding unique ID
            
        Returns:
            DeviceAgentBinding instance or None if not found
        """
        binding = await self.repo.find_by_id(binding_id)
        
        if binding:
            logger.info(f"Retrieved binding: {binding_id}")
        else:
            logger.warning(f"Binding not found: {binding_id}")
        
        return binding
    
    async def get_binding_by_device_id(self, device_id: str) -> Optional[DeviceAgentBinding]:
        """
        Get binding by device ID
        
        Args:
            device_id: Device unique ID
            
        Returns:
            DeviceAgentBinding instance or None if not found
        """
        binding = await self.repo.find_by_device_id(device_id)
        
        if binding:
            logger.info(f"Retrieved binding for device: {device_id}")
        else:
            logger.warning(f"No binding found for device: {device_id}")
        
        return binding
    
    async def get_bindings_by_agent_id(self, agent_id: str) -> list[DeviceAgentBinding]:
        """
        Get all bindings for an agent
        
        Args:
            agent_id: Agent unique ID
            
        Returns:
            List of DeviceAgentBinding instances
        """
        bindings = await self.repo.find_by_agent_id(agent_id)
        
        logger.info(f"Retrieved {len(bindings)} bindings for agent: {agent_id}")
        
        return bindings
    
    async def create_binding(self, binding_data: BindingOperation) -> DeviceAgentBinding:
        """
        Create or reactivate a device-agent binding
        
        Args:
            binding_data: Binding creation data
            
        Returns:
            Created or updated binding instance
            
        Raises:
            ValueError: If device or agent not found, or device already bound to this agent
        """
        # 1. Validate device exists
        device = await self.device_repo.find_by_id(binding_data.device_id)
        if not device:
            raise ValueError(f"Device not found: {binding_data.device_id}")
        
        # 2. Validate agent exists
        agent = await self.agent_repo.find_by_id(binding_data.agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {binding_data.agent_id}")
        
        # 3. Check if binding already exists for this device-agent pair
        existing_binding = await self.repo.find_by_device_and_agent(
            binding_data.device_id,
            binding_data.agent_id
        )
        
        if existing_binding:
            # Binding record exists
            if existing_binding.status == "bound":
                # Already bound - return error
                raise ValueError(
                    f"Device {binding_data.device_id} is already bound to agent {binding_data.agent_id}"
                )
            else:
                # Status is "unbound" - reactivate the binding
                existing_binding.status = "bound"
                existing_binding.updated_at = datetime.now(timezone.utc)
                binding = await self.repo.save(existing_binding)
                logger.info(
                    f"Reactivated binding: {existing_binding.id} "
                    f"(device={binding_data.device_id}, agent={binding_data.agent_id})"
                )
                return binding
        else:
            # No existing binding - create new one
            binding_id = id_generator.generate()
            binding = DeviceAgentBinding(
                id=binding_id,
                device_id=binding_data.device_id,
                agent_id=binding_data.agent_id,
                status="bound",
            )
            binding = await self.repo.save(binding)
            logger.info(
                f"Created new binding: {binding_id} "
                f"(device={binding_data.device_id}, agent={binding_data.agent_id})"
            )
            return binding
    
    async def update_binding(
        self,
        binding_id: str,
        binding_data: BindingUpdate
    ) -> Optional[DeviceAgentBinding]:
        """
        Update binding configuration
        
        Args:
            binding_id: Binding unique ID
            binding_data: Binding update data
            
        Returns:
            Updated binding instance or None if not found
            
        Raises:
            ValueError: If new agent not found
        """
        # Get existing binding
        binding = await self.repo.find_by_id(binding_id)
        if not binding:
            return None
        
        # Business logic: Validate new agent if provided
        if binding_data.agent_id:
            agent = await self.agent_repo.find_by_id(binding_data.agent_id)
            if not agent:
                raise ValueError(f"Agent not found: {binding_data.agent_id}")
            binding.agent_id = binding_data.agent_id
        
        # Business logic: Update status if provided
        if binding_data.status:
            binding.status = binding_data.status
        
        # Business logic: Update timestamp
        binding.updated_at = datetime.now(timezone.utc)
        
        # Persist changes
        binding = await self.repo.save(binding)
        
        logger.info(f"Updated binding: {binding_id}")
        
        return binding
    
    async def delete_binding(self, binding_id: str) -> bool:
        """
        Delete a binding
        
        Args:
            binding_id: Binding unique ID
            
        Returns:
            True if deleted, False if not found
        """
        binding = await self.repo.find_by_id(binding_id)
        if not binding:
            return False
        
        await self.repo.delete(binding)
        
        logger.info(f"Deleted binding: {binding_id}")
        
        return True
    
    async def unbind_device(self, device_id: str, agent_id: str) -> bool:
        """
        Unbind a device from an agent (update status to unbound)
        
        Args:
            device_id: Device unique ID
            agent_id: Agent unique ID
            
        Returns:
            True if unbound successfully, False if no active binding found
        """
        # Find the specific device-agent binding
        binding = await self.repo.find_by_device_and_agent(device_id, agent_id)
        if not binding:
            logger.warning(f"No binding found for device {device_id} and agent {agent_id}")
            return False
        
        # Check if already unbound
        if binding.status == "unbound":
            logger.info(f"Device {device_id} is already unbound from agent {agent_id}")
            return False
        
        # Update status to unbound instead of deleting
        binding.status = "unbound"
        binding.updated_at = datetime.now(timezone.utc)
        await self.repo.save(binding)
        
        logger.info(f"Unbound device {device_id} from agent {agent_id}")
        
        return True


def get_binding_service(db: AsyncSession) -> BindingService:
    """
    Dependency function to get Binding service
    
    Args:
        db: Database session
        
    Returns:
        BindingService instance
    """
    return BindingService(db)

