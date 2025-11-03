"""
DeviceAgentBinding Router

API endpoints for Device-Agent binding management.
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from orm import get_db
from services.binding_service import get_binding_service
from schemas.binding import BindingOperation, BindingResponse
from utils.response import ApiResponse, success_response, error_response


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bindings", tags=["bindings"])


@router.get("/device/{device_id}")
async def get_bindings_by_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Get device-agent binding information by device ID
    
    - **device_id**: Device unique ID
    
    Returns the binding relationship for the specified device, or null if not bound.
    """
    try:
        service = get_binding_service(db)
        binding = await service.get_binding_by_device_id(device_id)
        
        if not binding:
            # No binding is not an error - return success with null data
            return success_response(
                data=None
            )
        
        binding_response = BindingResponse.model_validate(binding)
        return success_response(data=binding_response)
        
    except Exception as e:
        logger.error(f"Error getting device binding: {str(e)}")
        return error_response(
            message=f"Failed to get device binding: {str(e)}",
            code=500
        )


@router.get("/agent/{agent_id}")
async def get_bindings_by_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Get all device bindings for an agent
    
    - **agent_id**: Agent unique ID
    
    Returns all devices bound to the specified agent (empty list if none).
    """
    try:
        service = get_binding_service(db)
        bindings = await service.get_bindings_by_agent_id(agent_id)
        
        binding_responses = [
            BindingResponse.model_validate(binding) for binding in bindings
        ]
        
        return success_response(
            data=binding_responses,
            message=f"Found {len(bindings)} device(s) bound to agent"
        )
        
    except Exception as e:
        logger.error(f"Error getting agent device bindings: {str(e)}")
        return error_response(
            message=f"Failed to get agent device bindings: {str(e)}",
            code=500
        )


@router.post("/bind")
async def create_device_agent_binding(
    binding_data: BindingOperation,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Create a device-agent binding (bind device to agent)
    
    Request body:
    - **deviceId**: Device unique ID (required)
    - **agentId**: Agent unique ID (required)
    
    Creates a binding relationship between the specified device and agent.
    
    Note: Each device can only be bound to one agent at a time.
    """
    try:
        service = get_binding_service(db)
        binding = await service.create_binding(binding_data)
        
        binding_response = BindingResponse.model_validate(binding)
        return success_response(
            data=binding_response,
            message="Device bound to agent successfully",
        )
        
    except ValueError as e:
        logger.warning(f"Validation error creating binding: {str(e)}")
        return error_response(
            message=str(e),
            code=400
        )
    except Exception as e:
        logger.error(f"Error creating binding: {str(e)}")
        return error_response(
            message=f"Failed to create binding: {str(e)}",
            code=500
        )


@router.post("/unbind")
async def unbind_device(
    binding_data: BindingOperation,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Unbind device from agent
    
    Request body:
    - **deviceId**: Device unique ID (required)
    - **agentId**: Agent unique ID (required)
    
    Updates the binding status to unbound for the specified device-agent pair.
    """
    try:
        service = get_binding_service(db)
        unbound = await service.unbind_device(
            binding_data.device_id,
            binding_data.agent_id
        )
        
        if not unbound:
            return error_response(
                message=f"No active binding found for device {binding_data.device_id} and agent {binding_data.agent_id}",
                code=404
            )
        
        return success_response(
            data={
                "deviceId": binding_data.device_id,
                "agentId": binding_data.agent_id
            },
            message="Device unbound from agent successfully"
        )
        
    except Exception as e:
        logger.error(f"Error unbinding device: {str(e)}")
        return error_response(
            message=f"Failed to unbind device: {str(e)}",
            code=500
        )

