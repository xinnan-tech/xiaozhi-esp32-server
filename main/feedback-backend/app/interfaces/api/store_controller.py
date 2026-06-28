"""门店管理控制器 - 后台管理用，需要认证"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.store_service import StoreService
from app.infrastructure.persistence.database import get_session
from app.interfaces.api.auth import get_current_user, require_super_admin

router = APIRouter(prefix="/store", tags=["门店管理"])


class CreateStoreRequest(BaseModel):
    store_code: str = Field(..., description="门店编码(6位数字)")
    store_name: str = Field(..., description="门店名称")
    manager: Optional[str] = Field(default=None, description="店长")
    shareholders: Optional[str] = Field(default=None, description="股东")
    agent_id: Optional[str] = Field(default=None, description="智能体ID")


class UpdateStoreRequest(BaseModel):
    store_code: Optional[str] = Field(default=None, description="门店编码")
    store_name: Optional[str] = Field(default=None, description="门店名称")
    manager: Optional[str] = Field(default=None, description="店长")
    shareholders: Optional[str] = Field(default=None, description="股东")
    agent_id: Optional[str] = Field(default=None, description="智能体ID")
    status: Optional[int] = Field(default=None, description="状态")


@router.get("/list")
async def list_stores(
    page: int = 1,
    page_size: int = 20,
    store_name: Optional[str] = None,
    status: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """分页查询门店列表"""
    require_super_admin(current_user)
    service = StoreService(session)
    result = await service.list_page(page, page_size, store_name, status)
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "list": [
                {
                    "id": s.id,
                    "storeCode": s.store_code,
                    "storeName": s.store_name,
                    "manager": s.manager,
                    "shareholders": s.shareholders,
                    "agentId": s.agent_id,
                    "status": s.status,
                    "createDate": str(s.create_date) if s.create_date else None,
                }
                for s in result["list"]
            ],
            "total": result["total"],
            "page": result["page"],
            "pageSize": result["page_size"],
        },
    }


@router.post("")
async def create_store(
    req: CreateStoreRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """创建门店"""
    require_super_admin(current_user)
    service = StoreService(session)
    store = await service.create_store(
        req.store_code, req.store_name, req.manager, req.shareholders, req.agent_id
    )
    return {"code": 0, "msg": "success", "data": {"id": store.id}}


@router.put("/{store_id}")
async def update_store(
    store_id: str,
    req: UpdateStoreRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """更新门店"""
    require_super_admin(current_user)
    service = StoreService(session)
    kwargs = {k: v for k, v in req.model_dump().items() if v is not None}
    store = await service.update_store(store_id, **kwargs)
    return {"code": 0, "msg": "success", "data": {"id": store.id}}


@router.post("/delete")
async def delete_store(
    store_id: str = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """删除门店"""
    require_super_admin(current_user)
    service = StoreService(session)
    await service.delete_store(store_id)
    return {"code": 0, "msg": "success"}
