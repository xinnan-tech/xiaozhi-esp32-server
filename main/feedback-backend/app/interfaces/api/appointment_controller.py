"""预约日历控制器"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.appointment_service import AppointmentService
from app.infrastructure.persistence.database import get_session
from app.interfaces.api.auth import get_current_user, scoped_store_id

router = APIRouter(prefix="/appointment", tags=["预约日历"])


class Payload(BaseModel):
    data: dict = Field(default_factory=dict)


@router.get("/calendar")
async def calendar(
    start_date: str = Query(...),
    end_date: str = Query(...),
    store_id: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = AppointmentService(session)
    data = await service.calendar(scoped_store_id(current_user, store_id), start_date, end_date, employee_id)
    return {"code": 0, "msg": "success", "data": data}


@router.get("/availability")
async def availability(
    date: str = Query(...),
    store_id: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    duration_minutes: int = Query(60, ge=15, le=480),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = AppointmentService(session)
    data = await service.availability(scoped_store_id(current_user, store_id), date, employee_id, duration_minutes)
    return {"code": 0, "msg": "success", "data": data}


@router.post("")
async def create_appointment(
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = payload.data
    data["store_id"] = scoped_store_id(current_user, data.get("store_id") or data.get("storeId"))
    try:
        service = AppointmentService(session)
        result = await service.create_appointment(data, current_user.get("username", ""))
        return {"code": 0, "msg": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{appointment_id}/confirm")
async def confirm_appointment(
    appointment_id: str,
    payload: Payload = Payload(),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = AppointmentService(session)
    result = await service.update_status(appointment_id, "confirmed", payload.data, current_user.get("username", ""))
    if not result:
        raise HTTPException(status_code=404, detail="预约不存在")
    return {"code": 0, "msg": "success", "data": result}


@router.post("/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = AppointmentService(session)
    result = await service.update_status(appointment_id, "cancelled", payload.data, current_user.get("username", ""))
    if not result:
        raise HTTPException(status_code=404, detail="预约不存在")
    return {"code": 0, "msg": "success", "data": result}


@router.post("/{appointment_id}/complete")
async def complete_appointment(
    appointment_id: str,
    payload: Payload = Payload(),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = AppointmentService(session)
    result = await service.update_status(appointment_id, "completed", payload.data, current_user.get("username", ""))
    if not result:
        raise HTTPException(status_code=404, detail="预约不存在")
    return {"code": 0, "msg": "success", "data": result}
