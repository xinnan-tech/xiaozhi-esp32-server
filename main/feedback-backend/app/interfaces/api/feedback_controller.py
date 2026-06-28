"""反馈记录管理控制器 - 后台管理用，需要认证"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.application.feedback_service import FeedbackService
from app.infrastructure.persistence.database import get_session
from app.infrastructure.persistence.models import CrmMemberModel, EmployeeModel, StoreModel
from app.interfaces.api.auth import get_current_user, scoped_store_id

router = APIRouter(prefix="/record", tags=["反馈记录管理"])


@router.get("/list")
async def list_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    employee_id: Optional[str] = Query(None),
    satisfaction: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """分页查询反馈记录"""
    service = FeedbackService(session)
    scoped_id = scoped_store_id(current_user, store_id)
    result = await service.list_records(
        page, page_size,
        store_id=scoped_id,
        employee_id=employee_id,
        satisfaction=satisfaction,
        start_date=start_date,
        end_date=end_date,
    )
    store_ids = {r.store_id for r in result["list"] if r.store_id}
    employee_ids = {r.employee_id for r in result["list"] if r.employee_id}
    stores = session.query(StoreModel).filter(StoreModel.id.in_(store_ids)).all() if store_ids else []
    employees = session.query(EmployeeModel).filter(EmployeeModel.id.in_(employee_ids)).all() if employee_ids else []
    store_map = {s.id: s.store_name for s in stores}
    employee_map = {e.id: e.name for e in employees}
    employee_no_map = {e.id: e.number for e in employees}
    member_ids = {r.member_id for r in result["list"] if r.member_id}
    members = session.query(CrmMemberModel).filter(CrmMemberModel.id.in_(member_ids)).all() if member_ids else []
    member_map = {m.id: m for m in members}
    return {
        "code": 0,
        "msg": "success",
        "data": {
            "list": [
                {
                    "id": r.id,
                    "sessionId": r.session_id,
                    "storeId": r.store_id,
                    "storeName": store_map.get(r.store_id, r.store_id),
                    "employeeId": r.employee_id,
                    "employeeName": employee_map.get(r.employee_id, r.employee_id),
                    "employeeNumber": employee_no_map.get(r.employee_id),
                    "deviceMac": r.device_mac,
                    "rawAsrText": r.raw_asr_text,
                    "cleanedText": r.cleaned_text,
                    "qaJson": r.qa_json,
                    "reviewLong": r.review_long,
                    "reviewShort": r.review_short,
                    "satisfaction": r.satisfaction,
                    "memberId": r.member_id,
                    "memberName": member_map[r.member_id].name if r.member_id in member_map else None,
                    "memberPhone": member_map[r.member_id].phone if r.member_id in member_map else None,
                    "customerName": r.customer_name,
                    "phoneTail": r.phone_tail,
                    "memberMatchStatus": r.member_match_status,
                    "memberMatchCandidates": r.member_match_candidates or [],
                    "visitId": r.visit_id,
                    "cardCloseId": r.card_close_id,
                    "status": r.status,
                    "createDate": str(r.create_date) if r.create_date else None,
                }
                for r in result["list"]
            ],
            "total": result["total"],
            "page": result["page"],
            "pageSize": result["page_size"],
        },
    }
