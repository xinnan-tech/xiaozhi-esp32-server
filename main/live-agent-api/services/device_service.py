from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.device import Device, AgentDeviceBinding, DeviceModel
from repositories.agent import Agent
from utils.exceptions import NotFoundException, BadRequestException
from schemas.device import (
    DeviceResponse,
    DeviceWithBindingsResponse,
    DeviceListResponse,
    AgentBindingResponse
)


class DeviceService:
    """Device service layer"""
    
    async def bind_device(
        self,
        db: AsyncSession,
        owner_id: str,
        device_id: str
    ) -> DeviceWithBindingsResponse:
        """
        Bind a device to user by device_id.
        If device exists but unbound, update owner.
        If device doesn't exist, create it.
        """
        device = await Device.get_by_id(db, device_id)
        
        if device:
            # Device exists
            if device.owner_id and device.owner_id != owner_id:
                raise BadRequestException("Device is bound to another user")
            
            # Update owner if not set
            if not device.owner_id:
                device = await Device.update_owner(db, device_id, owner_id)
        else:
            # Create new device
            device = await Device.create(db, device_id, owner_id)
        
        return await self._build_device_with_bindings(db, device)
    
    async def unbind_device(
        self,
        db: AsyncSession,
        owner_id: str,
        device_id: str
    ) -> None:
        """Unbind device: clear owner and all agent bindings"""
        device = await Device.get_by_id(db, device_id)
        if not device:
            raise NotFoundException("Device not found")
        
        if device.owner_id != owner_id:
            raise BadRequestException("Device does not belong to you")
        
        await Device.unbind(db, device_id)
    
    async def get_user_devices(
        self,
        db: AsyncSession,
        owner_id: str
    ) -> DeviceListResponse:
        """Get all devices owned by user"""
        devices = await Device.get_by_owner(db, owner_id)
        
        result = []
        for device in devices:
            device_with_bindings = await self._build_device_with_bindings(db, device)
            result.append(device_with_bindings)
        
        return DeviceListResponse(devices=result)
    
    async def add_agent_to_device(
        self,
        db: AsyncSession,
        owner_id: str,
        device_id: str,
        agent_id: str,
        is_default: bool = False
    ) -> DeviceWithBindingsResponse:
        """Add an agent binding to device"""
        device = await Device.get_by_id(db, device_id)
        if not device:
            raise NotFoundException("Device not found")
        
        if device.owner_id != owner_id:
            raise BadRequestException("Device does not belong to you")
        
        # Verify agent exists and belongs to user
        agent = await Agent.get_by_id(db, agent_id)
        if not agent:
            raise NotFoundException("Agent not found")
        if agent.owner_id != owner_id:
            raise BadRequestException("Agent does not belong to you")
        
        # Verify agent has wake_word configured (required for device binding)
        if not agent.wake_word:
            raise BadRequestException("Agent must have a wake word configured to bind to device")
        
        # Check if binding already exists
        existing = await AgentDeviceBinding.get_binding(db, device_id, agent_id)
        if existing:
            raise BadRequestException("Agent is already bound to this device")
        
        await AgentDeviceBinding.create(db, device_id, agent_id, is_default)
        
        return await self._build_device_with_bindings(db, device)
    
    async def remove_agent_from_device(
        self,
        db: AsyncSession,
        owner_id: str,
        device_id: str,
        agent_id: str
    ) -> DeviceWithBindingsResponse:
        """Remove an agent binding from device"""
        device = await Device.get_by_id(db, device_id)
        if not device:
            raise NotFoundException("Device not found")
        
        if device.owner_id != owner_id:
            raise BadRequestException("Device does not belong to you")
        
        # Check if binding exists
        binding = await AgentDeviceBinding.get_binding(db, device_id, agent_id)
        if not binding:
            raise NotFoundException("Binding not found")
        
        was_default = binding.is_default
        await AgentDeviceBinding.delete(db, device_id, agent_id)
        
        # If removed the default, set another as default
        if was_default:
            bindings = await AgentDeviceBinding.get_bindings_by_device(db, device_id)
            if bindings:
                await AgentDeviceBinding.set_default(db, device_id, bindings[0].agent_id)
        
        return await self._build_device_with_bindings(db, device)
    
    async def _build_device_with_bindings(
        self,
        db: AsyncSession,
        device: DeviceModel
    ) -> DeviceWithBindingsResponse:
        """Build device response with bindings"""
        bindings = await AgentDeviceBinding.get_bindings_by_device(db, device.device_id)
        
        return DeviceWithBindingsResponse(
            device_id=device.device_id,
            owner_id=device.owner_id,
            created_at=device.created_at,
            updated_at=device.updated_at,
            bindings=[
                AgentBindingResponse(
                    agent_id=b.agent_id,
                    is_default=b.is_default,
                    created_at=b.created_at
                )
                for b in bindings
            ]
        )


device_service = DeviceService()

