"""员工管理控制器 - 后台管理用，需要认证"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.employee_service import EmployeeService
from app.infrastructure.persistence.database import get_session
from app.interfaces.api.auth import get_current_user, scoped_store_id

router = APIRouter(prefix="/employee", tags=["员工管理"])


class CreateEmployeeRequest(BaseModel):
    name: str = Field(..., description="员工姓名")
    number: int = Field(..., description="工号")
    store_id: str = Field(..., description="门店ID")
    employee_type: str = Field(default="normal", description="员工类型")


class UpdateEmployeeRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="员工姓名")
    number: Optional[int] = Field(default=None, description="工号")
    store_id: Optional[str] = Field(default=None, description="门店ID")
    employee_type: Optional[str] = Field(default=None, description="员工类型")
    status: Optional[int] = Field(default=None, description="状态")


@router.get("/list")
async def list_employees(
    page: int = 1,
    page_size: int = 20,
    store_id: Optional[str] = None,
    name: Optional[str] = None,
    status: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """分页查询员工列表"""
    service = EmployeeService(session)
    result = await service.list_page(page, page_size, scoped_store_id(current_user, store_id), name, status)
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "list": [
                {
                    "id": e.id,
                    "name": e.name,
                    "number": e.number,
                    "storeId": e.store_id,
                    "employeeType": e.employee_type,
                    "status": e.status,
                    "createDate": str(e.create_date) if e.create_date else None,
                }
                for e in result["list"]
            ],
            "total": result["total"],
            "page": result["page"],
            "pageSize": result["page_size"],
        },
    }


@router.post("")
async def create_employee(
    req: CreateEmployeeRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """创建员工"""
    store_id = scoped_store_id(current_user, req.store_id)
    service = EmployeeService(session)
    employee = await service.create_employee(
        req.name, req.number, store_id, req.employee_type
    )
    return {"code": 0, "msg": "success", "data": {"id": employee.id}}


@router.put("/{employee_id}")
async def update_employee(
    employee_id: str,
    req: UpdateEmployeeRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """更新员工"""
    service = EmployeeService(session)
    existing = await service.get_by_id(employee_id)
    scoped_store_id(current_user, existing.store_id)
    kwargs = {k: v for k, v in req.model_dump().items() if v is not None}
    if "store_id" in kwargs:
        kwargs["store_id"] = scoped_store_id(current_user, kwargs["store_id"])
    employee = await service.update_employee(employee_id, **kwargs)
    return {"code": 0, "msg": "success", "data": {"id": employee.id}}


@router.post("/delete")
async def delete_employee(
    employee_id: str = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """删除员工"""
    service = EmployeeService(session)
    existing = await service.get_by_id(employee_id)
    scoped_store_id(current_user, existing.store_id)
    await service.delete_employee(employee_id)
    return {"code": 0, "msg": "success"}
