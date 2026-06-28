"""反馈记录仓储实现"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.feedback.entity import FeedbackRecord
from app.domain.feedback.repository import IFeedbackRecordRepository
from app.infrastructure.persistence.models import FeedbackRecordModel
from app.shared.utils import generate_id


class FeedbackRecordRepositoryImpl(IFeedbackRecordRepository):
    """反馈记录仓储实现"""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _to_entity(model: FeedbackRecordModel) -> FeedbackRecord:
        return FeedbackRecord(
            id=model.id,
            session_id=model.session_id,
            store_id=model.store_id,
            employee_id=model.employee_id,
            device_mac=model.device_mac,
            raw_asr_text=model.raw_asr_text,
            cleaned_text=model.cleaned_text,
            qa_json=model.qa_json if isinstance(model.qa_json, str) else (
                str(model.qa_json) if model.qa_json else None
            ),
            review_long=model.review_long,
            review_short=model.review_short,
            satisfaction=model.satisfaction,
            member_id=model.member_id,
            visit_id=model.visit_id,
            card_close_id=model.card_close_id,
            customer_name=model.customer_name,
            phone_tail=model.phone_tail,
            member_match_status=model.member_match_status,
            member_match_candidates=model.member_match_candidates,
            status=model.status,
            create_date=model.create_date,
            update_date=model.update_date,
        )

    @staticmethod
    def _to_model(entity: FeedbackRecord) -> FeedbackRecordModel:
        return FeedbackRecordModel(
            id=entity.id,
            session_id=entity.session_id,
            store_id=entity.store_id,
            employee_id=entity.employee_id,
            device_mac=entity.device_mac,
            raw_asr_text=entity.raw_asr_text,
            cleaned_text=entity.cleaned_text,
            qa_json=entity.qa_json,
            review_long=entity.review_long,
            review_short=entity.review_short,
            satisfaction=entity.satisfaction,
            member_id=entity.member_id,
            visit_id=entity.visit_id,
            card_close_id=entity.card_close_id,
            customer_name=entity.customer_name,
            phone_tail=entity.phone_tail,
            member_match_status=entity.member_match_status,
            member_match_candidates=entity.member_match_candidates,
            status=entity.status,
            create_date=entity.create_date or datetime.now(),
            update_date=entity.update_date or datetime.now(),
        )

    async def get_by_id(self, record_id: str) -> Optional[FeedbackRecord]:
        model = self.session.query(FeedbackRecordModel).filter(
            FeedbackRecordModel.id == record_id
        ).first()
        return self._to_entity(model) if model else None

    async def get_by_session_id(self, session_id: str) -> Optional[FeedbackRecord]:
        model = self.session.query(FeedbackRecordModel).filter(
            FeedbackRecordModel.session_id == session_id
        ).first()
        return self._to_entity(model) if model else None

    async def save(self, record: FeedbackRecord) -> FeedbackRecord:
        existing = self.session.query(FeedbackRecordModel).filter(
            FeedbackRecordModel.id == record.id
        ).first()
        if existing:
            for field in ["session_id", "store_id", "employee_id", "device_mac",
                          "raw_asr_text", "cleaned_text", "qa_json",
                          "review_long", "review_short", "satisfaction",
                          "member_id", "visit_id", "card_close_id",
                          "customer_name", "phone_tail", "member_match_status", "member_match_candidates", "status"]:
                setattr(existing, field, getattr(record, field))
            existing.update_date = datetime.now()
            self.session.commit()
            self.session.refresh(existing)
            return self._to_entity(existing)
        else:
            if not record.id:
                record.id = generate_id()
            model = self._to_model(record)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_entity(model)

    async def list_page(self, page: int = 1, page_size: int = 20,
                        store_id: Optional[str] = None,
                        employee_id: Optional[str] = None,
                        satisfaction: Optional[str] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        status: Optional[int] = None) -> dict:
        query = self.session.query(FeedbackRecordModel)

        if store_id:
            query = query.filter(FeedbackRecordModel.store_id == store_id)
        if employee_id:
            query = query.filter(FeedbackRecordModel.employee_id == employee_id)
        if satisfaction:
            query = query.filter(FeedbackRecordModel.satisfaction == satisfaction)
        if start_date:
            query = query.filter(FeedbackRecordModel.create_date >= start_date)
        if end_date:
            query = query.filter(FeedbackRecordModel.create_date <= end_date)
        if status is not None:
            query = query.filter(FeedbackRecordModel.status == status)

        total = query.count()
        models = query.order_by(FeedbackRecordModel.create_date.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return {
            "list": [self._to_entity(m) for m in models],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def count_by_store(self, store_id: str,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> int:
        query = self.session.query(func.count(FeedbackRecordModel.id)).filter(
            FeedbackRecordModel.store_id == store_id
        )
        if start_date:
            query = query.filter(FeedbackRecordModel.create_date >= start_date)
        if end_date:
            query = query.filter(FeedbackRecordModel.create_date <= end_date)
        return query.scalar() or 0

    async def count_by_satisfaction(self, store_id: Optional[str] = None,
                                     start_date: Optional[str] = None,
                                     end_date: Optional[str] = None) -> dict:
        query = self.session.query(
            FeedbackRecordModel.satisfaction,
            func.count(FeedbackRecordModel.id)
        ).filter(FeedbackRecordModel.satisfaction.isnot(None))

        if store_id:
            query = query.filter(FeedbackRecordModel.store_id == store_id)
        if start_date:
            query = query.filter(FeedbackRecordModel.create_date >= start_date)
        if end_date:
            query = query.filter(FeedbackRecordModel.create_date <= end_date)

        query = query.group_by(FeedbackRecordModel.satisfaction)
        results = query.all()

        return {row[0]: row[1] for row in results}

    async def get_daily_stats(self, store_id: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[dict]:
        """按天统计反馈数量"""
        query = self.session.query(
            func.date(FeedbackRecordModel.create_date).label("date"),
            func.count(FeedbackRecordModel.id).label("count"),
        )

        if store_id:
            query = query.filter(FeedbackRecordModel.store_id == store_id)
        if start_date:
            query = query.filter(FeedbackRecordModel.create_date >= start_date)
        if end_date:
            query = query.filter(FeedbackRecordModel.create_date <= end_date)

        query = query.group_by(func.date(FeedbackRecordModel.create_date)) \
            .order_by(func.date(FeedbackRecordModel.create_date))

        return [{"date": str(row.date), "count": row.count} for row in query.all()]
