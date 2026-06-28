"""统计分析应用服务 - 后台管理统计用例"""

from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import EmployeeModel, FeedbackRecordModel
from app.infrastructure.persistence.feedback_repo_impl import FeedbackRecordRepositoryImpl
from app.infrastructure.persistence.store_repo_impl import StoreRepositoryImpl
from app.infrastructure.persistence.employee_repo_impl import EmployeeRepositoryImpl


class StatsService:
    """统计分析应用服务"""

    def __init__(self, session: Session):
        self.session = session
        self.record_repo = FeedbackRecordRepositoryImpl(session)
        self.store_repo = StoreRepositoryImpl(session)
        self.employee_repo = EmployeeRepositoryImpl(session)

    async def get_overview(self, store_id: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Dict:
        """获取统计概览"""
        # 满意度分布
        satisfaction_stats = await self.record_repo.count_by_satisfaction(
            store_id, start_date, end_date
        )

        # 总记录数
        total = sum(satisfaction_stats.values())

        # 满意率
        positive = satisfaction_stats.get("very_satisfied", 0) + satisfaction_stats.get("satisfied", 0)
        satisfaction_rate = round(positive / total * 100, 1) if total > 0 else 0

        return {
            "total_records": total,
            "satisfaction_distribution": satisfaction_stats,
            "satisfaction_rate": satisfaction_rate,
            "very_satisfied": satisfaction_stats.get("very_satisfied", 0),
            "satisfied": satisfaction_stats.get("satisfied", 0),
            "unsatisfied": satisfaction_stats.get("unsatisfied", 0),
            "very_bad": satisfaction_stats.get("very_bad", 0),
        }

    async def get_daily_stats(self, store_id: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[Dict]:
        """获取按天统计"""
        return await self.record_repo.get_daily_stats(store_id, start_date, end_date)

    async def get_employee_kpi(self, store_id: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[Dict]:
        """按员工统计好/中/差评，用于店长 KPI。"""
        query = self.session.query(
            FeedbackRecordModel.employee_id,
            EmployeeModel.name.label("employee_name"),
            EmployeeModel.number.label("employee_number"),
            FeedbackRecordModel.satisfaction,
            func.count(FeedbackRecordModel.id).label("count"),
        ).outerjoin(EmployeeModel, FeedbackRecordModel.employee_id == EmployeeModel.id)
        if store_id:
            query = query.filter(FeedbackRecordModel.store_id == store_id)
        if start_date:
            query = query.filter(FeedbackRecordModel.create_date >= start_date)
        if end_date:
            query = query.filter(FeedbackRecordModel.create_date <= end_date)
        rows = query.group_by(
            FeedbackRecordModel.employee_id,
            EmployeeModel.name,
            EmployeeModel.number,
            FeedbackRecordModel.satisfaction,
        ).all()

        grouped = {}
        for row in rows:
            key = row.employee_id or "unknown"
            item = grouped.setdefault(key, {
                "employeeId": row.employee_id,
                "employeeName": row.employee_name or "未绑定员工",
                "employeeNumber": row.employee_number,
                "good": 0,
                "middle": 0,
                "bad": 0,
                "verySatisfied": 0,
                "satisfied": 0,
                "unsatisfied": 0,
                "veryBad": 0,
                "total": 0,
                "goodRate": 0,
            })
            count = row.count or 0
            sat = row.satisfaction
            item["total"] += count
            if sat == "very_satisfied":
                item["verySatisfied"] += count
                item["good"] += count
            elif sat == "satisfied":
                item["satisfied"] += count
                item["good"] += count
            elif sat == "unsatisfied":
                item["unsatisfied"] += count
                item["middle"] += count
            elif sat == "very_bad":
                item["veryBad"] += count
                item["bad"] += count
        result = list(grouped.values())
        for item in result:
            item["goodRate"] = round(item["good"] / item["total"] * 100, 1) if item["total"] else 0
        return sorted(result, key=lambda x: (x["goodRate"], x["good"], -x["bad"]), reverse=True)

    async def get_employee_records(self, employee_id: str, store_id: Optional[str] = None,
                                   satisfaction_group: Optional[str] = None,
                                   start_date: Optional[str] = None,
                                   end_date: Optional[str] = None,
                                   page: int = 1, page_size: int = 20) -> Dict:
        """查询某员工完整评价列表。"""
        query = self.session.query(FeedbackRecordModel).filter(FeedbackRecordModel.employee_id == employee_id)
        if store_id:
            query = query.filter(FeedbackRecordModel.store_id == store_id)
        if start_date:
            query = query.filter(FeedbackRecordModel.create_date >= start_date)
        if end_date:
            query = query.filter(FeedbackRecordModel.create_date <= end_date)
        if satisfaction_group == "good":
            query = query.filter(FeedbackRecordModel.satisfaction.in_(["very_satisfied", "satisfied"]))
        elif satisfaction_group == "middle":
            query = query.filter(FeedbackRecordModel.satisfaction == "unsatisfied")
        elif satisfaction_group == "bad":
            query = query.filter(FeedbackRecordModel.satisfaction == "very_bad")
        total = query.count()
        rows = query.order_by(FeedbackRecordModel.create_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {
            "list": [{
                "id": r.id,
                "employeeId": r.employee_id,
                "storeId": r.store_id,
                "satisfaction": r.satisfaction,
                "reviewLong": r.review_long,
                "reviewShort": r.review_short,
                "cleanedText": r.cleaned_text,
                "rawAsrText": r.raw_asr_text,
                "qaJson": r.qa_json,
                "memberId": r.member_id,
                "visitId": r.visit_id,
                "createDate": str(r.create_date) if r.create_date else None,
            } for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def get_single_store_stats(self, store_id: str, start_date: Optional[str] = None,
                                     end_date: Optional[str] = None) -> List[Dict]:
        """获取单门店统计"""
        store = await self.store_repo.get_by_id(store_id)
        if not store:
            return []
        count = await self.record_repo.count_by_store(store.id, start_date, end_date)
        satisfaction = await self.record_repo.count_by_satisfaction(store.id, start_date, end_date)
        total = sum(satisfaction.values())
        positive = satisfaction.get("very_satisfied", 0) + satisfaction.get("satisfied", 0)
        rate = round(positive / total * 100, 1) if total > 0 else 0
        return [{
            "store_id": store.id,
            "store_name": store.store_name,
            "store_code": store.store_code,
            "total_records": count,
            "satisfaction_rate": rate,
            "satisfaction_distribution": satisfaction,
        }]

    async def get_store_stats(self, start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[Dict]:
        """获取按门店统计"""
        stores = await self.store_repo.list_all(status=1)
        result = []
        for store in stores:
            result.extend(await self.get_single_store_stats(store.id, start_date, end_date))
        return result
