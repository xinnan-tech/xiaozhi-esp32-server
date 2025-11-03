"""
Device Router

API endpoints for Device management.
"""

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orm import get_db
from services.device_service import DeviceService, get_device_service
from schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceListQuery,
)
from utils.response import (
    ApiResponse,
    success_response,
    error_response,
    paginated_response,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/device", tags=["device"])


@router.get("/")
async def get_device_list(
    search: Annotated[str | None, Query(description="Search keyword")] = None,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize", description="Items per page")] = 10,
    sortBy: Annotated[str, Query(alias="sortBy", description="Sort field")] = "createdAt",
    sortOrder: Annotated[str, Query(alias="sortOrder", pattern="^(asc|desc)$", description="Sort order")] = "desc",
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Get Device list with search, filtering, pagination and sorting
    
    - **search**: Search keyword (searches in name, device_id, and model)
    - **status**: Filter by status (active, inactive, offline)
    - **page**: Page number (starting from 1)
    - **pageSize**: Number of items per page (1-100)
    - **sortBy**: Field to sort by (default: createdAt)
    - **sortOrder**: Sort order - asc or desc (default: desc)
    
    Returns paginated list of devices with total count.
    """
    try:
        # Create query object
        query = DeviceListQuery(
            search=search,
            status=status,
            page=page,
            page_size=pageSize,
            sort_by=sortBy,
            sort_order=sortOrder,
        )
        
        # Get service
        service = get_device_service(db)
        
        # Get devices
        devices, total = await service.get_device_list(query)
        
        # Convert to response format
        device_responses = [
            DeviceResponse.model_validate(device) for device in devices
        ]
        
        # Create paginated response
        pagination_data = paginated_response(
            items=device_responses,
            total=total,
            page=page,
            page_size=pageSize,
        )
        
        return success_response(data=pagination_data)
        
    except Exception as e:
        logger.error(f"Error getting device list: {str(e)}")
        return error_response(
            message=f"Failed to get device list: {str(e)}",
            code=500
        )


@router.get("/{device_id}")
async def get_device_detail(
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Get Device details by ID
    
    - **device_id**: Device unique ID
    
    Returns detailed device information.
    """
    try:
        service = get_device_service(db)
        device = await service.get_device_by_id(device_id)
        
        if not device:
            return error_response(
                message=f"Device not found: {device_id}",
                code=404
            )
        
        device_response = DeviceResponse.model_validate(device)
        return success_response(data=device_response)
        
    except Exception as e:
        logger.error(f"Error getting device detail: {str(e)}")
        return error_response(
            message=f"Failed to get device detail: {str(e)}",
            code=500
        )


@router.post("/")
async def create_device(
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Create a new Device
    
    Request body:
    - **name**: Device display name (required)
    - **deviceId**: Device hardware ID (required, must be unique)
    - **model**: Device model (optional)
    - **firmwareVersion**: Firmware version (optional)
    - **status**: Device status (default: active)
    - **description**: Device description (optional)
    - **metadata**: Additional metadata in JSON format (optional)
    
    Returns the created device with generated ID.
    """
    try:
        service = get_device_service(db)
        device = await service.create_device(device_data)
        
        device_response = DeviceResponse.model_validate(device)
        return success_response(
            data=device_response,
            message="Device created successfully",
            code=201
        )
        
    except ValueError as e:
        # Business logic errors (e.g., duplicate device_id)
        logger.warning(f"Validation error creating device: {str(e)}")
        return error_response(
            message=str(e),
            code=400
        )
    except Exception as e:
        logger.error(f"Error creating device: {str(e)}")
        return error_response(
            message=f"Failed to create device: {str(e)}",
            code=500
        )


@router.put("/{device_id}")
async def update_device(
    device_id: str,
    device_data: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Update Device configuration
    
    - **device_id**: Device unique ID
    
    Request body (all fields optional):
    - **name**: Device display name
    - **model**: Device model
    - **firmwareVersion**: Firmware version
    - **status**: Device status
    - **isOnline**: Whether device is online
    - **description**: Device description
    - **metadata**: Additional metadata
    
    Returns the updated device information.
    """
    try:
        service = get_device_service(db)
        device = await service.update_device(device_id, device_data)
        
        if not device:
            return error_response(
                message=f"Device not found: {device_id}",
                code=404
            )
        
        device_response = DeviceResponse.model_validate(device)
        return success_response(
            data=device_response,
            message="Device updated successfully"
        )
        
    except Exception as e:
        logger.error(f"Error updating device: {str(e)}")
        return error_response(
            message=f"Failed to update device: {str(e)}",
            code=500
        )


@router.delete("/{device_id}")
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Delete a Device
    
    - **device_id**: Device unique ID
    
    Deletes the device if no binding relationships exist.
    Returns success message if deleted.
    """
    try:
        service = get_device_service(db)
        deleted = await service.delete_device(device_id)
        
        if not deleted:
            return error_response(
                message=f"Device not found: {device_id}",
                code=404
            )
        
        return success_response(
            data={"id": device_id},
            message="Device deleted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error deleting device: {str(e)}")
        return error_response(
            message=f"Failed to delete device: {str(e)}",
            code=500
        )

