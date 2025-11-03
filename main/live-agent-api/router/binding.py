"""
DeviceAgentBinding Router

API endpoints for Device-Agent binding management.
"""

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orm import get_db
from services.binding_service import BindingService, get_binding_service
from schemas.binding import (
    BindingCreate,
    BindingUpdate,
    BindingResponse,
    BindingListQuery,
)
from utils.response import (
    ApiResponse,
    success_response,
    error_response,
    paginated_response,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/binding", tags=["binding"])


@router.get("/")
async def get_binding_list(
    deviceId: Annotated[str | None, Query(alias="deviceId", description="Filter by device ID")] = None,
    agentId: Annotated[str | None, Query(alias="agentId", description="Filter by agent ID")] = None,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize", description="Items per page")] = 10,
    sortBy: Annotated[str, Query(alias="sortBy", description="Sort field")] = "createdAt",
    sortOrder: Annotated[str, Query(alias="sortOrder", pattern="^(asc|desc)$", description="Sort order")] = "desc",
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Get DeviceAgentBinding list with filtering, pagination and sorting
    
    - **deviceId**: Filter by device ID
    - **agentId**: Filter by agent ID
    - **status**: Filter by status (active, inactive)
    - **page**: Page number (starting from 1)
    - **pageSize**: Number of items per page (1-100)
    - **sortBy**: Field to sort by (default: createdAt)
    - **sortOrder**: Sort order - asc or desc (default: desc)
    
    Returns paginated list of bindings with total count.
    """
    try:
        # Create query object
        query = BindingListQuery(
            device_id=deviceId,
            agent_id=agentId,
            status=status,
            page=page,
            page_size=pageSize,
            sort_by=sortBy,
            sort_order=sortOrder,
        )
        
        # Get service
        service = get_binding_service(db)
        
        # Get bindings
        bindings, total = await service.get_binding_list(query)
        
        # Convert to response format
        binding_responses = [
            BindingResponse.model_validate(binding) for binding in bindings
        ]
        
        # Create paginated response
        pagination_data = paginated_response(
            items=binding_responses,
            total=total,
            page=page,
            page_size=pageSize,
        )
        
        return success_response(data=pagination_data)
        
    except Exception as e:
        logger.error(f"Error getting binding list: {str(e)}")
        return error_response(
            message=f"Failed to get binding list: {str(e)}",
            code=500
        )


@router.get("/{binding_id}")
async def get_binding_detail(
    binding_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Get DeviceAgentBinding details by ID
    
    - **binding_id**: Binding unique ID
    
    Returns detailed binding information.
    """
    try:
        service = get_binding_service(db)
        binding = await service.get_binding_by_id(binding_id)
        
        if not binding:
            return error_response(
                message=f"Binding not found: {binding_id}",
                code=404
            )
        
        binding_response = BindingResponse.model_validate(binding)
        return success_response(data=binding_response)
        
    except Exception as e:
        logger.error(f"Error getting binding detail: {str(e)}")
        return error_response(
            message=f"Failed to get binding detail: {str(e)}",
            code=500
        )


@router.get("/device/{device_id}")
async def get_binding_by_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Get DeviceAgentBinding by device ID
    
    - **device_id**: Device unique ID
    
    Returns binding information for the device.
    """
    try:
        service = get_binding_service(db)
        binding = await service.get_binding_by_device_id(device_id)
        
        if not binding:
            return error_response(
                message=f"No binding found for device: {device_id}",
                code=404
            )
        
        binding_response = BindingResponse.model_validate(binding)
        return success_response(data=binding_response)
        
    except Exception as e:
        logger.error(f"Error getting binding by device: {str(e)}")
        return error_response(
            message=f"Failed to get binding by device: {str(e)}",
            code=500
        )


@router.post("/")
async def create_binding(
    binding_data: BindingCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Create a new DeviceAgentBinding
    
    Request body:
    - **deviceId**: Device unique ID (required)
    - **agentId**: Agent unique ID (required)
    
    Returns the created binding with generated ID.
    
    Note: Each device can only be bound to one agent at a time.
    """
    try:
        service = get_binding_service(db)
        binding = await service.create_binding(binding_data)
        
        binding_response = BindingResponse.model_validate(binding)
        return success_response(
            data=binding_response,
            message="Binding created successfully",
            code=201
        )
        
    except ValueError as e:
        # Business logic errors (e.g., device not found, already bound)
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


@router.put("/{binding_id}")
async def update_binding(
    binding_id: str,
    binding_data: BindingUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Update DeviceAgentBinding configuration
    
    - **binding_id**: Binding unique ID
    
    Request body (all fields optional):
    - **agentId**: Agent unique ID (to change the bound agent)
    - **status**: Binding status (active, inactive)
    
    Returns the updated binding information.
    """
    try:
        service = get_binding_service(db)
        binding = await service.update_binding(binding_id, binding_data)
        
        if not binding:
            return error_response(
                message=f"Binding not found: {binding_id}",
                code=404
            )
        
        binding_response = BindingResponse.model_validate(binding)
        return success_response(
            data=binding_response,
            message="Binding updated successfully"
        )
        
    except ValueError as e:
        # Business logic errors (e.g., agent not found)
        logger.warning(f"Validation error updating binding: {str(e)}")
        return error_response(
            message=str(e),
            code=400
        )
    except Exception as e:
        logger.error(f"Error updating binding: {str(e)}")
        return error_response(
            message=f"Failed to update binding: {str(e)}",
            code=500
        )


@router.delete("/{binding_id}")
async def delete_binding(
    binding_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Delete a DeviceAgentBinding
    
    - **binding_id**: Binding unique ID
    
    Deletes the binding relationship between device and agent.
    Returns success message if deleted.
    """
    try:
        service = get_binding_service(db)
        deleted = await service.delete_binding(binding_id)
        
        if not deleted:
            return error_response(
                message=f"Binding not found: {binding_id}",
                code=404
            )
        
        return success_response(
            data={"id": binding_id},
            message="Binding deleted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error deleting binding: {str(e)}")
        return error_response(
            message=f"Failed to delete binding: {str(e)}",
            code=500
        )


@router.delete("/device/{device_id}")
async def unbind_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Remove binding for a device
    
    - **device_id**: Device unique ID
    
    Unbinds the device from its agent.
    Returns success message if unbound.
    """
    try:
        service = get_binding_service(db)
        unbound = await service.unbind_device(device_id)
        
        if not unbound:
            return error_response(
                message=f"No binding found for device: {device_id}",
                code=404
            )
        
        return success_response(
            data={"deviceId": device_id},
            message="Device unbound successfully"
        )
        
    except Exception as e:
        logger.error(f"Error unbinding device: {str(e)}")
        return error_response(
            message=f"Failed to unbind device: {str(e)}",
            code=500
        )

