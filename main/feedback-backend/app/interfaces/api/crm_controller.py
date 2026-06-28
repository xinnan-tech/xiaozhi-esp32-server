"""CRM 控制器 - 客户档案、到店、账户、销卡、建议、问题闭环"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application.crm_service import CrmService
from app.infrastructure.persistence.database import get_session
from app.interfaces.api.auth import get_current_user, scoped_store_id
from app.shared.mekai66 import MEKAI66_FIELDS

router = APIRouter(prefix="/crm", tags=["CRM管理"])


class Payload(BaseModel):
    data: dict = Field(default_factory=dict)


@router.get("/overview")
async def overview(
    store_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    return {"code": 0, "msg": "success", "data": await service.get_overview(scoped_store_id(current_user, store_id))}


@router.get("/mekai66-fields")
async def get_mekai66_fields(
    current_user: dict = Depends(get_current_user),
):
    """麦凯66客户档案字段"""
    return {"code": 0, "msg": "success", "data": MEKAI66_FIELDS}


@router.get("/member/list")
async def list_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    status: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.list_members(page, page_size, scoped_store_id(current_user, store_id), keyword, status)
    return {"code": 0, "msg": "success", "data": data}


@router.get("/member/{member_id}")
async def get_member(
    member_id: str,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.get_member(member_id, scoped_store_id(current_user))
    if not data:
        raise HTTPException(status_code=404, detail="客户不存在")
    return {"code": 0, "msg": "success", "data": data}


@router.post("/member")
async def create_member(
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = payload.data
    data["store_id"] = scoped_store_id(current_user, data.get("store_id") or data.get("storeId"))
    if not data.get("store_id"):
        raise HTTPException(status_code=400, detail="请选择门店")
    service = CrmService(session)
    return {"code": 0, "msg": "success", "data": await service.create_member(data, current_user.get("username", ""))}


@router.put("/member/{member_id}")
async def update_member(
    member_id: str,
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.update_member(member_id, payload.data, scoped_store_id(current_user), current_user.get("username", ""))
    if not data:
        raise HTTPException(status_code=404, detail="客户不存在")
    return {"code": 0, "msg": "success", "data": data}


@router.get("/visit/list")
async def list_visits(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    member_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.list_visits(page, page_size, scoped_store_id(current_user, store_id), member_id)
    return {"code": 0, "msg": "success", "data": data}


@router.post("/visit")
async def create_visit(
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = payload.data
    data["store_id"] = scoped_store_id(current_user, data.get("store_id") or data.get("storeId"))
    if not data.get("store_id"):
        raise HTTPException(status_code=400, detail="请选择门店")
    service = CrmService(session)
    return {"code": 0, "msg": "success", "data": await service.create_visit(data, current_user.get("username", ""))}


@router.put("/visit/{visit_id}")
async def update_visit(
    visit_id: str,
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.update_visit(visit_id, payload.data, scoped_store_id(current_user), current_user.get("username", ""))
    if not data:
        raise HTTPException(status_code=404, detail="到店记录不存在")
    return {"code": 0, "msg": "success", "data": data}


@router.get("/account/list")
async def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    member_id: Optional[str] = Query(None),
    status: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.list_accounts(page, page_size, scoped_store_id(current_user, store_id), member_id, status)
    return {"code": 0, "msg": "success", "data": data}


@router.post("/account")
async def create_account(
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = payload.data
    data["store_id"] = scoped_store_id(current_user, data.get("store_id") or data.get("storeId"))
    if not data.get("store_id"):
        raise HTTPException(status_code=400, detail="请选择门店")
    service = CrmService(session)
    return {"code": 0, "msg": "success", "data": await service.create_account(data, current_user.get("username", ""))}


@router.get("/account/transactions")
async def list_account_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    member_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.list_account_transactions(page, page_size, scoped_store_id(current_user, store_id), account_id, member_id)
    return {"code": 0, "msg": "success", "data": data}


@router.post("/account/{account_id}/consume")
async def consume_account(
    account_id: str,
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.consume_account(account_id, payload.data, scoped_store_id(current_user), current_user.get("username", ""))
    if not data:
        raise HTTPException(status_code=404, detail="账户不存在")
    return {"code": 0, "msg": "success", "data": data}


@router.post("/card-close")
async def close_card(
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.close_card(payload.data, scoped_store_id(current_user), current_user.get("username", ""))
    if not data:
        raise HTTPException(status_code=404, detail="账户不存在")
    return {"code": 0, "msg": "success", "data": data}


@router.get("/card-close/list")
async def list_card_closes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    member_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.list_card_closes(page, page_size, scoped_store_id(current_user, store_id), member_id)
    return {"code": 0, "msg": "success", "data": data}


@router.get("/body-status/list")
async def list_body_statuses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    member_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.list_body_statuses(page, page_size, scoped_store_id(current_user, store_id), member_id)
    return {"code": 0, "msg": "success", "data": data}


@router.post("/body-status")
async def create_body_status(
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = payload.data
    data["store_id"] = scoped_store_id(current_user, data.get("store_id") or data.get("storeId"))
    if not data.get("store_id"):
        raise HTTPException(status_code=400, detail="请选择门店")
    service = CrmService(session)
    return {"code": 0, "msg": "success", "data": await service.create_body_status(data, current_user.get("username", ""))}


@router.get("/product/list")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.list_products(page, page_size, scoped_store_id(current_user, store_id), keyword, category, status)
    return {"code": 0, "msg": "success", "data": data}


@router.post("/product")
async def create_product(
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = payload.data
    data["store_id"] = scoped_store_id(current_user, data.get("store_id") or data.get("storeId"))
    if not data.get("store_id"):
        raise HTTPException(status_code=400, detail="请选择门店")
    service = CrmService(session)
    return {"code": 0, "msg": "success", "data": await service.create_product(data, current_user.get("username", ""))}


@router.get("/member-product/list")
async def list_member_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    member_id: Optional[str] = Query(None),
    status: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.list_member_products(page, page_size, scoped_store_id(current_user, store_id), member_id, status)
    return {"code": 0, "msg": "success", "data": data}


@router.post("/member-product/purchase")
async def purchase_product(
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = payload.data
    data["store_id"] = scoped_store_id(current_user, data.get("store_id") or data.get("storeId"))
    if not data.get("store_id"):
        raise HTTPException(status_code=400, detail="请选择门店")
    service = CrmService(session)
    return {"code": 0, "msg": "success", "data": await service.purchase_product(data, current_user.get("username", ""))}


@router.post("/member-product/{member_product_id}/consume")
async def consume_member_product(
    member_product_id: str,
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.consume_member_product(member_product_id, payload.data, scoped_store_id(current_user), current_user.get("username", ""))
    if not data:
        raise HTTPException(status_code=404, detail="客户产品不存在")
    return {"code": 0, "msg": "success", "data": data}


@router.get("/product-consume/list")
async def list_product_consumes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    member_id: Optional[str] = Query(None),
    member_product_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.list_product_consumes(page, page_size, scoped_store_id(current_user, store_id), member_id, member_product_id)
    return {"code": 0, "msg": "success", "data": data}


@router.get("/suggestion/list")
async def list_suggestions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.list_suggestions(page, page_size, scoped_store_id(current_user, store_id), status)
    return {"code": 0, "msg": "success", "data": data}


@router.post("/suggestion")
async def create_suggestion(
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = payload.data
    data["store_id"] = scoped_store_id(current_user, data.get("store_id") or data.get("storeId"))
    if not data.get("store_id"):
        raise HTTPException(status_code=400, detail="请选择门店")
    service = CrmService(session)
    return {"code": 0, "msg": "success", "data": await service.create_suggestion(data, current_user.get("username", ""))}


@router.post("/suggestion/{suggestion_id}/status")
async def update_suggestion_status(
    suggestion_id: str,
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    status = payload.data.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="缺少状态")
    service = CrmService(session)
    data = await service.update_suggestion_status(suggestion_id, status, payload.data, scoped_store_id(current_user), current_user.get("username", ""))
    if not data:
        raise HTTPException(status_code=404, detail="建议不存在")
    return {"code": 0, "msg": "success", "data": data}


@router.get("/issue/list")
async def list_issues(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.list_issues(page, page_size, scoped_store_id(current_user, store_id), status)
    return {"code": 0, "msg": "success", "data": data}


@router.post("/issue")
async def create_issue(
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    data = payload.data
    data["store_id"] = scoped_store_id(current_user, data.get("store_id") or data.get("storeId"))
    if not data.get("store_id"):
        raise HTTPException(status_code=400, detail="请选择门店")
    service = CrmService(session)
    return {"code": 0, "msg": "success", "data": await service.create_issue(data, current_user.get("username", ""))}


@router.put("/issue/{issue_id}")
async def update_issue(
    issue_id: str,
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.update_issue(issue_id, payload.data, scoped_store_id(current_user), current_user.get("username", ""))
    if not data:
        raise HTTPException(status_code=404, detail="问题不存在")
    return {"code": 0, "msg": "success", "data": data}


@router.post("/feedback/{feedback_id}/bind")
async def bind_feedback(
    feedback_id: str,
    payload: Payload,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    service = CrmService(session)
    data = await service.bind_feedback(feedback_id, payload.data, scoped_store_id(current_user))
    if not data:
        raise HTTPException(status_code=404, detail="反馈不存在")
    return {"code": 0, "msg": "success", "data": data}
