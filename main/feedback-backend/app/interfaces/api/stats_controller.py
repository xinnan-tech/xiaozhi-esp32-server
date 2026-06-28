"""统计控制器 - 后台管理用"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.application.stats_service import StatsService
from app.infrastructure.persistence.database import get_session
from app.interfaces.api.auth import get_current_user, scoped_store_id

router = APIRouter(prefix="/stats", tags=["统计分析"])


@router.get("/overview")
async def get_overview(
    store_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """统计概览"""
    service = StatsService(session)
    result = await service.get_overview(scoped_store_id(current_user, store_id), start_date, end_date)
    return {"code": 0, "msg": "success", "data": result}


@router.get("/daily")
async def get_daily_stats(
    store_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """按天统计"""
    service = StatsService(session)
    result = await service.get_daily_stats(scoped_store_id(current_user, store_id), start_date, end_date)
    return {"code": 0, "msg": "success", "data": result}


@router.get("/employee-kpi")
async def get_employee_kpi(
    store_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """按员工统计好/中/差评 KPI"""
    service = StatsService(session)
    result = await service.get_employee_kpi(scoped_store_id(current_user, store_id), start_date, end_date)
    return {"code": 0, "msg": "success", "data": result}


@router.get("/employee-records")
async def get_employee_records(
    employee_id: str = Query(...),
    satisfaction_group: Optional[str] = Query(None, description="good/middle/bad"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    store_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """查询某员工完整评价列表"""
    service = StatsService(session)
    result = await service.get_employee_records(
        employee_id=employee_id,
        store_id=scoped_store_id(current_user, store_id),
        satisfaction_group=satisfaction_group,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return {"code": 0, "msg": "success", "data": result}


@router.get("/by-store")
async def get_store_stats(
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """按门店统计"""
    service = StatsService(session)
    store_id = scoped_store_id(current_user)
    if store_id:
        result = await service.get_single_store_stats(store_id, start_date, end_date)
    else:
        result = await service.get_store_stats(start_date, end_date)
    return {"code": 0, "msg": "success", "data": result}
