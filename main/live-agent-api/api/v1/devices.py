from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db
from services.device_service import device_service
from utils.response import success_response
from api.auth import get_current_user_id
from schemas.device import (
    DeviceBindRequest,
    DeviceAddAgentRequest
)

router = APIRouter()


@router.post("/bind", summary="Bind device")
async def bind_device(
    request: DeviceBindRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Bind a device to user by device_id.
    
    - If device doesn't exist, creates it
    - If device exists but unbound, binds to current user
    """
    device = await device_service.bind_device(
        db=db,
        owner_id=current_user_id,
        device_id=request.device_id
    )
    return success_response(data=device.model_dump())


@router.delete("/{device_id}", summary="Unbind device")
async def unbind_device(
    device_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Unbind a device.
    
    - Clears owner_id (device record preserved)
    - Removes all agent bindings
    """
    await device_service.unbind_device(
        db=db,
        owner_id=current_user_id,
        device_id=device_id
    )
    return success_response(data={}, message="Device unbound successfully")


@router.get("", summary="Get user's devices")
async def get_devices(
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get all devices owned by current user with their agent bindings"""
    devices = await device_service.get_user_devices(
        db=db,
        owner_id=current_user_id
    )
    return success_response(data=devices.model_dump())


@router.post("/{device_id}/agents", summary="Add agent to device")
async def add_agent_to_device(
    device_id: str,
    request: DeviceAddAgentRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Add an agent binding to device"""
    device = await device_service.add_agent_to_device(
        db=db,
        owner_id=current_user_id,
        device_id=device_id,
        agent_id=request.agent_id,
        is_default=request.is_default
    )
    return success_response(data=device.model_dump())


@router.delete("/{device_id}/agents/{agent_id}", summary="Remove agent from device")
async def remove_agent_from_device(
    device_id: str,
    agent_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove an agent binding from device.
    
    If removed agent was default, another binding will be set as default.
    """
    device = await device_service.remove_agent_from_device(
        db=db,
        owner_id=current_user_id,
        device_id=device_id,
        agent_id=agent_id
    )
    return success_response(data=device.model_dump())


@router.get("/{device_id}/agents", summary="Get device's bound agents")
async def get_device_bound_agents(
    device_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get all agents bound to a specific device"""
    result = await device_service.get_device_bound_agents(
        db=db,
        owner_id=current_user_id,
        device_id=device_id
    )
    return success_response(data=result.model_dump())


