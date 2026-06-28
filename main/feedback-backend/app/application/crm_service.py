"""CRM 应用服务 - 客户档案、到店、账户、销卡、建议、问题闭环"""

import hashlib
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.infrastructure.persistence.models import (
    CrmAccountModel,
    CrmAccountTransactionModel,
    CrmBodyStatusModel,
    CrmCardCloseModel,
    CrmIssueModel,
    CrmMemberModel,
    CrmMemberProductModel,
    CrmProductConsumeModel,
    CrmProductModel,
    CrmSuggestionModel,
    CrmVisitModel,
    FeedbackRecordModel,
)
from app.shared.utils import generate_id


class CrmService:
    """CRM 应用服务"""

    def __init__(self, session: Session):
        self.session = session

    # ---- Member ----
    async def list_members(self, page: int = 1, page_size: int = 20,
                           store_id: Optional[str] = None, keyword: Optional[str] = None,
                           status: Optional[int] = None) -> dict:
        query = self.session.query(CrmMemberModel)
        if store_id:
            query = query.filter(CrmMemberModel.store_id == store_id)
        if keyword:
            like = f"%{keyword}%"
            query = query.filter((CrmMemberModel.name.like(like)) | (CrmMemberModel.phone.like(like)))
        if status is not None:
            query = query.filter(CrmMemberModel.status == status)
        total = query.count()
        rows = query.order_by(CrmMemberModel.update_date.desc()) \
            .offset((page - 1) * page_size).limit(page_size).all()
        return {"list": [self._member_to_dict(m) for m in rows], "total": total, "page": page, "page_size": page_size}

    async def get_member(self, member_id: str, store_id: Optional[str] = None) -> Optional[dict]:
        query = self.session.query(CrmMemberModel).filter(CrmMemberModel.id == member_id)
        if store_id:
            query = query.filter(CrmMemberModel.store_id == store_id)
        member = query.first()
        if not member:
            return None
        data = self._member_to_dict(member)
        data["visits"] = [self._visit_to_dict(v) for v in self.session.query(CrmVisitModel)
                           .filter(CrmVisitModel.member_id == member.id)
                           .order_by(CrmVisitModel.arrive_at.desc(), CrmVisitModel.create_date.desc()).limit(10).all()]
        data["accounts"] = [self._account_to_dict(a) for a in self.session.query(CrmAccountModel)
                             .filter(CrmAccountModel.member_id == member.id).order_by(CrmAccountModel.create_date.desc()).all()]
        data["transactions"] = [self._transaction_to_dict(t) for t in self.session.query(CrmAccountTransactionModel)
                                .filter(CrmAccountTransactionModel.member_id == member.id)
                                .order_by(CrmAccountTransactionModel.create_date.desc()).limit(20).all()]
        data["products"] = [self._member_product_to_dict(p) for p in self.session.query(CrmMemberProductModel)
                             .filter(CrmMemberProductModel.member_id == member.id)
                             .order_by(CrmMemberProductModel.create_date.desc()).all()]
        data["productConsumes"] = [self._product_consume_to_dict(c) for c in self.session.query(CrmProductConsumeModel)
                                    .filter(CrmProductConsumeModel.member_id == member.id)
                                    .order_by(CrmProductConsumeModel.create_date.desc()).limit(20).all()]
        data["bodyStatuses"] = [self._body_status_to_dict(b) for b in self.session.query(CrmBodyStatusModel)
                                 .filter(CrmBodyStatusModel.member_id == member.id)
                                 .order_by(CrmBodyStatusModel.record_date.desc()).limit(20).all()]
        data["feedbacks"] = [self._feedback_to_dict(r) for r in self.session.query(FeedbackRecordModel)
                              .filter(FeedbackRecordModel.member_id == member.id)
                              .order_by(FeedbackRecordModel.create_date.desc()).limit(10).all()]
        data["suggestions"] = [self._suggestion_to_dict(s) for s in self.session.query(CrmSuggestionModel)
                                .filter(CrmSuggestionModel.member_id == member.id)
                                .order_by(CrmSuggestionModel.create_date.desc()).limit(10).all()]
        data["issues"] = [self._issue_to_dict(i) for i in self.session.query(CrmIssueModel)
                           .filter(CrmIssueModel.member_id == member.id)
                           .order_by(CrmIssueModel.create_date.desc()).limit(10).all()]
        return data

    async def create_member(self, data: dict, operator: str = "") -> dict:
        member = CrmMemberModel(
            id=generate_id(),
            store_id=data.get("store_id"),
            name=data.get("name"),
            phone=data.get("phone"),
            gender=data.get("gender"),
            birthday=self._parse_date(data.get("birthday")),
            wechat=data.get("wechat"),
            source=data.get("source") or "manual",
            level=data.get("level"),
            tags=data.get("tags"),
            mekai_tags=data.get("mekai_tags") or data.get("mekaiTags"),
            beauty_concerns=data.get("beauty_concerns") or data.get("beautyConcerns"),
            health_issues=data.get("health_issues") or data.get("healthIssues"),
            allergies=data.get("allergies"),
            service_preferences=data.get("service_preferences") or data.get("servicePreferences"),
            notes=data.get("notes"),
            creator=operator,
            updater=operator,
        )
        self.session.add(member)
        self.session.commit()
        self.session.refresh(member)
        return self._member_to_dict(member)

    async def update_member(self, member_id: str, data: dict, store_id: Optional[str] = None,
                            operator: str = "") -> Optional[dict]:
        query = self.session.query(CrmMemberModel).filter(CrmMemberModel.id == member_id)
        if store_id:
            query = query.filter(CrmMemberModel.store_id == store_id)
        member = query.first()
        if not member:
            return None
        mapping = {
            "name": "name", "phone": "phone", "gender": "gender", "wechat": "wechat",
            "level": "level", "tags": "tags", "allergies": "allergies", "notes": "notes", "status": "status",
        }
        for key, field in mapping.items():
            if key in data:
                setattr(member, field, data[key])
        if "birthday" in data:
            member.birthday = self._parse_date(data.get("birthday"))
        for key, field in [("mekai_tags", "mekai_tags"), ("mekaiTags", "mekai_tags"),
                           ("beauty_concerns", "beauty_concerns"), ("beautyConcerns", "beauty_concerns"),
                           ("health_issues", "health_issues"), ("healthIssues", "health_issues"),
                           ("service_preferences", "service_preferences"), ("servicePreferences", "service_preferences")]:
            if key in data:
                setattr(member, field, data[key])
        member.updater = operator
        member.update_date = datetime.now()
        self.session.commit()
        self.session.refresh(member)
        return self._member_to_dict(member)

    # ---- Visit ----
    async def list_visits(self, page: int = 1, page_size: int = 20,
                          store_id: Optional[str] = None, member_id: Optional[str] = None) -> dict:
        query = self.session.query(CrmVisitModel)
        if store_id:
            query = query.filter(CrmVisitModel.store_id == store_id)
        if member_id:
            query = query.filter(CrmVisitModel.member_id == member_id)
        total = query.count()
        rows = query.order_by(CrmVisitModel.arrive_at.desc(), CrmVisitModel.create_date.desc()) \
            .offset((page - 1) * page_size).limit(page_size).all()
        return {"list": [self._visit_to_dict(v) for v in rows], "total": total, "page": page, "page_size": page_size}

    async def create_visit(self, data: dict, operator: str = "") -> dict:
        arrive_at = self._parse_datetime(data.get("arrive_at") or data.get("arriveAt"))
        leave_at = self._parse_datetime(data.get("leave_at") or data.get("leaveAt"))
        duration = data.get("duration_minutes") or data.get("durationMinutes")
        if not duration and arrive_at and leave_at:
            duration = max(0, int((leave_at - arrive_at).total_seconds() // 60))
        visit = CrmVisitModel(
            id=generate_id(),
            store_id=data.get("store_id"),
            member_id=data.get("member_id") or data.get("memberId"),
            employee_id=data.get("employee_id") or data.get("employeeId"),
            feedback_record_id=data.get("feedback_record_id") or data.get("feedbackRecordId"),
            session_id=data.get("session_id") or data.get("sessionId"),
            device_mac=data.get("device_mac") or data.get("deviceMac"),
            visit_type=data.get("visit_type") or data.get("visitType") or "walk_in",
            service_items=data.get("service_items") or data.get("serviceItems"),
            arrive_at=arrive_at,
            leave_at=leave_at,
            duration_minutes=duration,
            satisfaction=data.get("satisfaction"),
            consumption_amount=self._decimal(data.get("consumption_amount") or data.get("consumptionAmount")),
            notes=data.get("notes"),
            creator=operator,
            updater=operator,
        )
        self.session.add(visit)
        self._touch_member_visit_stats(visit.member_id, visit.arrive_at, visit.consumption_amount)
        self.session.commit()
        self.session.refresh(visit)
        return self._visit_to_dict(visit)

    async def update_visit(self, visit_id: str, data: dict, store_id: Optional[str] = None,
                           operator: str = "") -> Optional[dict]:
        query = self.session.query(CrmVisitModel).filter(CrmVisitModel.id == visit_id)
        if store_id:
            query = query.filter(CrmVisitModel.store_id == store_id)
        visit = query.first()
        if not visit:
            return None
        for key, field in [("member_id", "member_id"), ("memberId", "member_id"),
                           ("employee_id", "employee_id"), ("employeeId", "employee_id"),
                           ("feedback_record_id", "feedback_record_id"), ("feedbackRecordId", "feedback_record_id"),
                           ("satisfaction", "satisfaction"), ("notes", "notes"),
                           ("service_items", "service_items"), ("serviceItems", "service_items")]:
            if key in data:
                setattr(visit, field, data[key])
        if "arrive_at" in data or "arriveAt" in data:
            visit.arrive_at = self._parse_datetime(data.get("arrive_at") or data.get("arriveAt"))
        if "leave_at" in data or "leaveAt" in data:
            visit.leave_at = self._parse_datetime(data.get("leave_at") or data.get("leaveAt"))
        if "duration_minutes" in data or "durationMinutes" in data:
            visit.duration_minutes = data.get("duration_minutes") or data.get("durationMinutes")
        elif visit.arrive_at and visit.leave_at:
            visit.duration_minutes = max(0, int((visit.leave_at - visit.arrive_at).total_seconds() // 60))
        if "consumption_amount" in data or "consumptionAmount" in data:
            visit.consumption_amount = self._decimal(data.get("consumption_amount") or data.get("consumptionAmount"))
        visit.updater = operator
        visit.update_date = datetime.now()
        self.session.commit()
        self.session.refresh(visit)
        return self._visit_to_dict(visit)

    # ---- Account ----
    async def list_accounts(self, page: int = 1, page_size: int = 20,
                            store_id: Optional[str] = None, member_id: Optional[str] = None,
                            status: Optional[int] = None) -> dict:
        query = self.session.query(CrmAccountModel)
        if store_id:
            query = query.filter(CrmAccountModel.store_id == store_id)
        if member_id:
            query = query.filter(CrmAccountModel.member_id == member_id)
        if status is not None:
            query = query.filter(CrmAccountModel.status == status)
        total = query.count()
        rows = query.order_by(CrmAccountModel.create_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {"list": [self._account_to_dict(a) for a in rows], "total": total, "page": page, "page_size": page_size}

    async def create_account(self, data: dict, operator: str = "") -> dict:
        total_amount = self._decimal(data.get("total_amount") or data.get("totalAmount"))
        balance_amount = self._decimal(data.get("balance_amount") or data.get("balanceAmount") or total_amount)
        account = CrmAccountModel(
            id=generate_id(),
            store_id=data.get("store_id"),
            member_id=data.get("member_id") or data.get("memberId"),
            account_type=data.get("account_type") or data.get("accountType") or "balance",
            card_name=data.get("card_name") or data.get("cardName"),
            total_amount=total_amount,
            balance_amount=balance_amount,
            total_count=data.get("total_count") or data.get("totalCount") or 0,
            balance_count=data.get("balance_count") or data.get("balanceCount") or data.get("total_count") or data.get("totalCount") or 0,
            valid_start=self._parse_date(data.get("valid_start") or data.get("validStart")),
            valid_end=self._parse_date(data.get("valid_end") or data.get("validEnd")),
            notes=data.get("notes"),
            creator=operator,
            updater=operator,
        )
        self.session.add(account)
        self.session.flush()
        self._add_transaction(account, "recharge", balance_amount, account.balance_count, 0, balance_amount, None, "开卡", operator)
        self.session.commit()
        self.session.refresh(account)
        return self._account_to_dict(account)

    async def list_account_transactions(self, page: int = 1, page_size: int = 20,
                                        store_id: Optional[str] = None,
                                        account_id: Optional[str] = None,
                                        member_id: Optional[str] = None) -> dict:
        query = self.session.query(CrmAccountTransactionModel)
        if store_id:
            query = query.filter(CrmAccountTransactionModel.store_id == store_id)
        if account_id:
            query = query.filter(CrmAccountTransactionModel.account_id == account_id)
        if member_id:
            query = query.filter(CrmAccountTransactionModel.member_id == member_id)
        total = query.count()
        rows = query.order_by(CrmAccountTransactionModel.create_date.desc()) \
            .offset((page - 1) * page_size).limit(page_size).all()
        return {"list": [self._transaction_to_dict(t) for t in rows], "total": total, "page": page, "page_size": page_size}

    async def consume_account(self, account_id: str, data: dict, store_id: Optional[str] = None,
                              operator: str = "") -> Optional[dict]:
        account = self._get_account(account_id, store_id)
        if not account:
            return None
        amount = self._decimal(data.get("amount"))
        count_change = int(data.get("count_change") or data.get("countChange") or 0)
        before = self._decimal(account.balance_amount)
        account.balance_amount = before - amount
        account.balance_count = int(account.balance_count or 0) - count_change
        account.update_date = datetime.now()
        visit_id = data.get("visit_id") or data.get("visitId") or self._latest_visit_id(account.member_id, account.store_id)
        if visit_id:
            self._sync_visit_consumption(visit_id, amount)
        self._add_transaction(account, "consume", -amount, -count_change, before, account.balance_amount,
                              visit_id, data.get("notes"), operator)
        self.session.commit()
        self.session.refresh(account)
        return self._account_to_dict(account)

    async def close_card(self, data: dict, store_id: Optional[str] = None, operator: str = "") -> Optional[dict]:
        account = self._get_account(data.get("account_id") or data.get("accountId"), store_id)
        if not account:
            return None
        close = CrmCardCloseModel(
            id=generate_id(),
            store_id=account.store_id,
            member_id=account.member_id,
            account_id=account.id,
            feedback_record_id=data.get("feedback_record_id") or data.get("feedbackRecordId"),
            close_type=data.get("close_type") or data.get("closeType") or "refund",
            reason=data.get("reason"),
            refund_amount=self._decimal(data.get("refund_amount") or data.get("refundAmount")),
            remaining_count=account.balance_count or 0,
            status=data.get("status") or "done",
            handled_by=operator,
            handle_notes=data.get("handle_notes") or data.get("handleNotes"),
        )
        account.status = 0
        account.closed_reason = close.reason
        account.closed_at = datetime.now()
        self.session.add(close)
        self._add_transaction(account, "close", -self._decimal(close.refund_amount), 0,
                              self._decimal(account.balance_amount), self._decimal(account.balance_amount),
                              None, close.reason, operator)
        if close.feedback_record_id:
            self.session.query(FeedbackRecordModel).filter(FeedbackRecordModel.id == close.feedback_record_id).update({
                "member_id": account.member_id,
                "card_close_id": close.id,
            })
        self.session.commit()
        self.session.refresh(close)
        return self._card_close_to_dict(close)

    async def list_card_closes(self, page: int = 1, page_size: int = 20,
                               store_id: Optional[str] = None, member_id: Optional[str] = None) -> dict:
        query = self.session.query(CrmCardCloseModel)
        if store_id:
            query = query.filter(CrmCardCloseModel.store_id == store_id)
        if member_id:
            query = query.filter(CrmCardCloseModel.member_id == member_id)
        total = query.count()
        rows = query.order_by(CrmCardCloseModel.create_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {"list": [self._card_close_to_dict(c) for c in rows], "total": total, "page": page, "page_size": page_size}

    # ---- Body Status ----
    async def list_body_statuses(self, page: int = 1, page_size: int = 20,
                                 store_id: Optional[str] = None, member_id: Optional[str] = None) -> dict:
        query = self.session.query(CrmBodyStatusModel)
        if store_id:
            query = query.filter(CrmBodyStatusModel.store_id == store_id)
        if member_id:
            query = query.filter(CrmBodyStatusModel.member_id == member_id)
        total = query.count()
        rows = query.order_by(CrmBodyStatusModel.record_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {"list": [self._body_status_to_dict(b) for b in rows], "total": total, "page": page, "page_size": page_size}

    async def create_body_status(self, data: dict, operator: str = "") -> dict:
        body_status = CrmBodyStatusModel(
            id=generate_id(), store_id=data.get("store_id"),
            member_id=data.get("member_id") or data.get("memberId"),
            visit_id=data.get("visit_id") or data.get("visitId"),
            member_product_id=data.get("member_product_id") or data.get("memberProductId"),
            record_date=self._parse_datetime(data.get("record_date") or data.get("recordDate")) or datetime.now(),
            weight=self._decimal(data.get("weight")) if data.get("weight") not in (None, "") else None,
            waistline=self._decimal(data.get("waistline")) if data.get("waistline") not in (None, "") else None,
            pain_level=data.get("pain_level") or data.get("painLevel"),
            sleep_quality=data.get("sleep_quality") or data.get("sleepQuality"),
            skin_status=data.get("skin_status") or data.get("skinStatus"),
            body_parts=data.get("body_parts") or data.get("bodyParts"),
            metrics=data.get("metrics"), notes=data.get("notes"),
            creator=operator, updater=operator,
        )
        self.session.add(body_status)
        self._merge_body_status_to_member(body_status)
        self.session.commit()
        self.session.refresh(body_status)
        return self._body_status_to_dict(body_status)

    def _merge_body_status_to_member(self, body_status):
        member = self.session.query(CrmMemberModel).filter(CrmMemberModel.id == body_status.member_id).first()
        if not member:
            return
        issues = member.health_issues if isinstance(member.health_issues, list) else []
        if isinstance(issues, str):
            try:
                issues = json.loads(issues)
            except Exception:
                issues = [issues]
        summary = []
        metrics = body_status.metrics if isinstance(body_status.metrics, dict) else {}
        if metrics.get("name"):
            summary.append(f"{metrics.get('name')}:{metrics.get('status') or ''}{'(' + str(metrics.get('value')) + ')' if metrics.get('value') else ''}")
        if body_status.notes:
            summary.append(body_status.notes)
        if summary:
            text = "；".join(summary)
            if text not in issues:
                issues.append(text)
                member.health_issues = issues
                member.update_date = datetime.now()

    # ---- Product / Package ----
    async def list_products(self, page: int = 1, page_size: int = 20,
                            store_id: Optional[str] = None, keyword: Optional[str] = None,
                            category: Optional[str] = None, status: Optional[int] = None) -> dict:
        query = self.session.query(CrmProductModel)
        if store_id:
            query = query.filter(CrmProductModel.store_id == store_id)
        if keyword:
            query = query.filter(CrmProductModel.product_name.like(f"%{keyword}%"))
        if category:
            query = query.filter(CrmProductModel.category == category)
        if status is not None:
            query = query.filter(CrmProductModel.status == status)
        total = query.count()
        rows = query.order_by(CrmProductModel.create_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {"list": [self._product_to_dict(p) for p in rows], "total": total, "page": page, "page_size": page_size}

    async def create_product(self, data: dict, operator: str = "") -> dict:
        product = CrmProductModel(
            id=generate_id(), store_id=data.get("store_id"),
            product_name=data.get("product_name") or data.get("productName"),
            product_type=data.get("product_type") or data.get("productType") or "service",
            category=data.get("category"), price=self._decimal(data.get("price")),
            default_count=int(data.get("default_count") or data.get("defaultCount") or 1),
            description=data.get("description"), creator=operator, updater=operator,
        )
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        return self._product_to_dict(product)

    async def list_member_products(self, page: int = 1, page_size: int = 20,
                                   store_id: Optional[str] = None, member_id: Optional[str] = None,
                                   status: Optional[int] = None) -> dict:
        query = self.session.query(CrmMemberProductModel)
        if store_id:
            query = query.filter(CrmMemberProductModel.store_id == store_id)
        if member_id:
            query = query.filter(CrmMemberProductModel.member_id == member_id)
        if status is not None:
            query = query.filter(CrmMemberProductModel.status == status)
        total = query.count()
        rows = query.order_by(CrmMemberProductModel.create_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {"list": [self._member_product_to_dict(p) for p in rows], "total": total, "page": page, "page_size": page_size}

    async def purchase_product(self, data: dict, operator: str = "") -> dict:
        product_id = data.get("product_id") or data.get("productId")
        product = self.session.query(CrmProductModel).filter(CrmProductModel.id == product_id).first() if product_id else None
        total_count = int(data.get("total_count") or data.get("totalCount") or data.get("purchase_count") or data.get("purchaseCount") or (product.default_count if product else 1) or 0)
        unit_price = self._decimal(data.get("unit_price") or data.get("unitPrice") or (product.price if product else 0))
        discount = self._decimal(data.get("discount") or 1)
        total_amount = self._decimal(data.get("total_amount") or data.get("totalAmount") or (unit_price * total_count * discount))
        valid_start = self._parse_date(data.get("valid_start") or data.get("validStart")) or datetime.now().date()
        valid_end = self._parse_date(data.get("valid_end") or data.get("validEnd")) or (valid_start + timedelta(days=365))
        member_product = CrmMemberProductModel(
            id=generate_id(), store_id=data.get("store_id"),
            member_id=data.get("member_id") or data.get("memberId"), product_id=product_id,
            account_id=data.get("account_id") or data.get("accountId"),
            product_name=data.get("product_name") or data.get("productName") or (product.product_name if product else "产品套餐"),
            package_items=data.get("package_items") or data.get("packageItems"),
            unit_price=unit_price, purchase_count=total_count, discount=discount,
            total_count=total_count, balance_count=int(data.get("balance_count") or data.get("balanceCount") or total_count),
            total_amount=total_amount, balance_amount=self._decimal(data.get("balance_amount") or data.get("balanceAmount") or total_amount),
            valid_start=valid_start,
            valid_end=valid_end,
            notes=data.get("notes"), creator=operator, updater=operator,
        )
        self.session.add(member_product)
        self.session.commit()
        self.session.refresh(member_product)
        return self._member_product_to_dict(member_product)

    def consume_member_product_sync(self, member_product_id: str, data: dict,
                                    store_id: Optional[str] = None, operator: str = ""):
        query = self.session.query(CrmMemberProductModel).filter(CrmMemberProductModel.id == member_product_id)
        if store_id:
            query = query.filter(CrmMemberProductModel.store_id == store_id)
        member_product = query.first()
        if not member_product:
            return None
        count = int(data.get("consume_count") or data.get("consumeCount") or 1)
        amount = self._decimal(data.get("consume_amount") or data.get("consumeAmount") or 0)
        member_product.balance_count = max(0, int(member_product.balance_count or 0) - count)
        member_product.balance_amount = max(Decimal("0"), self._decimal(member_product.balance_amount) - amount)
        if member_product.balance_count == 0 and self._decimal(member_product.balance_amount) == 0:
            member_product.status = 0
        member_product.update_date = datetime.now()
        visit_id = data.get("visit_id") or data.get("visitId") or self._latest_visit_id(member_product.member_id, member_product.store_id)
        if visit_id and amount:
            self._sync_visit_consumption(visit_id, amount)
        consume = CrmProductConsumeModel(
            id=generate_id(), store_id=member_product.store_id, member_id=member_product.member_id,
            member_product_id=member_product.id, product_id=member_product.product_id, visit_id=visit_id,
            consume_count=count, consume_amount=amount,
            balance_count_after=member_product.balance_count, balance_amount_after=member_product.balance_amount,
            notes=data.get("notes"), operator=operator,
        )
        self.session.add(consume)
        return member_product

    async def consume_member_product(self, member_product_id: str, data: dict,
                                     store_id: Optional[str] = None, operator: str = "") -> Optional[dict]:
        member_product = self.consume_member_product_sync(member_product_id, data, store_id, operator)
        if not member_product:
            return None
        self.session.commit()
        self.session.refresh(member_product)
        return self._member_product_to_dict(member_product)

    def _consume_member_product_old_unused(self, member_product_id: str, data: dict,
                                     store_id: Optional[str] = None, operator: str = "") -> Optional[dict]:
        query = self.session.query(CrmMemberProductModel).filter(CrmMemberProductModel.id == member_product_id)
        if store_id:
            query = query.filter(CrmMemberProductModel.store_id == store_id)
        member_product = query.first()
        if not member_product:
            return None
        count = int(data.get("consume_count") or data.get("consumeCount") or 1)
        amount = self._decimal(data.get("consume_amount") or data.get("consumeAmount") or 0)
        member_product.balance_count = max(0, int(member_product.balance_count or 0) - count)
        member_product.balance_amount = max(Decimal("0"), self._decimal(member_product.balance_amount) - amount)
        if member_product.balance_count == 0 and self._decimal(member_product.balance_amount) == 0:
            member_product.status = 0
        member_product.update_date = datetime.now()
        visit_id = data.get("visit_id") or data.get("visitId") or self._latest_visit_id(member_product.member_id, member_product.store_id)
        if visit_id and amount:
            self._sync_visit_consumption(visit_id, amount)
        consume = CrmProductConsumeModel(
            id=generate_id(), store_id=member_product.store_id, member_id=member_product.member_id,
            member_product_id=member_product.id, product_id=member_product.product_id, visit_id=visit_id,
            consume_count=count, consume_amount=amount,
            balance_count_after=member_product.balance_count, balance_amount_after=member_product.balance_amount,
            notes=data.get("notes"), operator=operator,
        )
        self.session.add(consume)
        self.session.commit()
        self.session.refresh(member_product)
        return self._member_product_to_dict(member_product)

    async def list_product_consumes(self, page: int = 1, page_size: int = 20,
                                    store_id: Optional[str] = None,
                                    member_id: Optional[str] = None,
                                    member_product_id: Optional[str] = None) -> dict:
        query = self.session.query(CrmProductConsumeModel)
        if store_id:
            query = query.filter(CrmProductConsumeModel.store_id == store_id)
        if member_id:
            query = query.filter(CrmProductConsumeModel.member_id == member_id)
        if member_product_id:
            query = query.filter(CrmProductConsumeModel.member_product_id == member_product_id)
        total = query.count()
        rows = query.order_by(CrmProductConsumeModel.create_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {"list": [self._product_consume_to_dict(c) for c in rows], "total": total, "page": page, "page_size": page_size}

    # ---- Suggestion / Issue ----
    async def list_suggestions(self, page: int = 1, page_size: int = 20,
                               store_id: Optional[str] = None, status: Optional[str] = None) -> dict:
        query = self.session.query(CrmSuggestionModel)
        if store_id:
            query = query.filter(CrmSuggestionModel.store_id == store_id)
        if status:
            query = query.filter(CrmSuggestionModel.status == status)
        total = query.count()
        rows = query.order_by(CrmSuggestionModel.frequency.desc(), CrmSuggestionModel.create_date.desc()) \
            .offset((page - 1) * page_size).limit(page_size).all()
        return {"list": [self._suggestion_to_dict(s) for s in rows], "total": total, "page": page, "page_size": page_size}

    async def create_suggestion(self, data: dict, operator: str = "") -> dict:
        content = (data.get("content") or "").strip()
        content_hash = self._content_hash(content)
        store_id = data.get("store_id")
        existing = self.session.query(CrmSuggestionModel).filter(
            CrmSuggestionModel.store_id == store_id,
            CrmSuggestionModel.content_hash == content_hash,
        ).first()
        if existing:
            existing.frequency = (existing.frequency or 1) + 1
            existing.update_date = datetime.now()
            self.session.commit()
            self.session.refresh(existing)
            return self._suggestion_to_dict(existing)
        suggestion = CrmSuggestionModel(
            id=generate_id(), store_id=store_id,
            feedback_record_id=data.get("feedback_record_id") or data.get("feedbackRecordId"),
            member_id=data.get("member_id") or data.get("memberId"),
            content=content, content_hash=content_hash,
            category=data.get("category") or self._suggestion_category(content),
            tags=data.get("tags") or self._suggestion_tags(content),
            priority=data.get("priority") or self._suggestion_priority(content),
            source=data.get("source") or "manual",
            submitter_name=data.get("submitter_name") or data.get("submitterName") or self._member_name(data.get("member_id") or data.get("memberId")),
            duplicate_group_id=generate_id(),
            status=data.get("status") or "pending", handled_by=operator,
        )
        self.session.add(suggestion)
        self.session.commit()
        self.session.refresh(suggestion)
        return self._suggestion_to_dict(suggestion)

    async def update_suggestion_status(self, suggestion_id: str, status: str, data: dict,
                                       store_id: Optional[str] = None, operator: str = "") -> Optional[dict]:
        query = self.session.query(CrmSuggestionModel).filter(CrmSuggestionModel.id == suggestion_id)
        if store_id:
            query = query.filter(CrmSuggestionModel.store_id == store_id)
        suggestion = query.first()
        if not suggestion:
            return None
        suggestion.status = status
        suggestion.handled_by = operator
        suggestion.handle_notes = data.get("handle_notes") or data.get("handleNotes") or suggestion.handle_notes
        suggestion.rejected_reason = data.get("rejected_reason") or data.get("rejectedReason") or suggestion.rejected_reason
        if status == "adopted":
            suggestion.adopted_at = datetime.now()
        suggestion.update_date = datetime.now()
        self.session.commit()
        self.session.refresh(suggestion)
        return self._suggestion_to_dict(suggestion)

    async def list_issues(self, page: int = 1, page_size: int = 20,
                          store_id: Optional[str] = None, status: Optional[str] = None) -> dict:
        query = self.session.query(CrmIssueModel)
        if store_id:
            query = query.filter(CrmIssueModel.store_id == store_id)
        if status:
            query = query.filter(CrmIssueModel.status == status)
        total = query.count()
        rows = query.order_by(CrmIssueModel.create_date.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return {"list": [self._issue_to_dict(i) for i in rows], "total": total, "page": page, "page_size": page_size}

    async def create_issue(self, data: dict, operator: str = "") -> dict:
        issue = CrmIssueModel(
            id=generate_id(), store_id=data.get("store_id"),
            feedback_record_id=data.get("feedback_record_id") or data.get("feedbackRecordId"),
            member_id=data.get("member_id") or data.get("memberId"),
            card_close_id=data.get("card_close_id") or data.get("cardCloseId"),
            title=data.get("title"), description=data.get("description"),
            severity=data.get("severity") or "medium", category=data.get("category"),
            status=data.get("status") or "identified",
            fix_plan=data.get("fix_plan") or data.get("fixPlan"),
            fix_deadline=self._parse_datetime(data.get("fix_deadline") or data.get("fixDeadline")),
            assigned_to=data.get("assigned_to") or data.get("assignedTo"),
        )
        self.session.add(issue)
        self.session.commit()
        self.session.refresh(issue)
        return self._issue_to_dict(issue)

    async def update_issue(self, issue_id: str, data: dict, store_id: Optional[str] = None,
                           operator: str = "") -> Optional[dict]:
        query = self.session.query(CrmIssueModel).filter(CrmIssueModel.id == issue_id)
        if store_id:
            query = query.filter(CrmIssueModel.store_id == store_id)
        issue = query.first()
        if not issue:
            return None
        for key, field in [("title", "title"), ("description", "description"), ("severity", "severity"),
                           ("category", "category"), ("status", "status"), ("fix_plan", "fix_plan"),
                           ("fixPlan", "fix_plan"), ("fix_result", "fix_result"), ("fixResult", "fix_result"),
                           ("assigned_to", "assigned_to"), ("assignedTo", "assigned_to")]:
            if key in data:
                setattr(issue, field, data[key])
        if issue.status == "fixed" and not issue.fixed_at:
            issue.fixed_at = datetime.now()
        if issue.status == "closed" and not issue.closed_at:
            issue.closed_at = datetime.now()
        issue.update_date = datetime.now()
        self.session.commit()
        self.session.refresh(issue)
        return self._issue_to_dict(issue)

    async def bind_feedback(self, feedback_id: str, data: dict, store_id: Optional[str] = None) -> Optional[dict]:
        query = self.session.query(FeedbackRecordModel).filter(FeedbackRecordModel.id == feedback_id)
        if store_id:
            query = query.filter(FeedbackRecordModel.store_id == store_id)
        record = query.first()
        if not record:
            return None
        for key, field in [("member_id", "member_id"), ("memberId", "member_id"),
                           ("visit_id", "visit_id"), ("visitId", "visit_id"),
                           ("card_close_id", "card_close_id"), ("cardCloseId", "card_close_id")]:
            if key in data:
                setattr(record, field, data[key])
        self.session.commit()
        self.session.refresh(record)
        return self._feedback_to_dict(record)

    async def get_overview(self, store_id: Optional[str] = None) -> dict:
        def count(model, *filters):
            q = self.session.query(func.count(model.id))
            if store_id and hasattr(model, "store_id"):
                q = q.filter(model.store_id == store_id)
            for f in filters:
                q = q.filter(f)
            return q.scalar() or 0
        total_balance = self.session.query(func.coalesce(func.sum(CrmAccountModel.balance_amount), 0))
        if store_id:
            total_balance = total_balance.filter(CrmAccountModel.store_id == store_id)
        return {
            "members": count(CrmMemberModel),
            "visits": count(CrmVisitModel),
            "activeAccounts": count(CrmAccountModel, CrmAccountModel.status == 1),
            "accountBalance": float(total_balance.scalar() or 0),
            "cardCloses": count(CrmCardCloseModel),
            "pendingSuggestions": count(CrmSuggestionModel, CrmSuggestionModel.status == "pending"),
            "adoptedSuggestions": count(CrmSuggestionModel, CrmSuggestionModel.status == "adopted"),
            "openIssues": count(CrmIssueModel, CrmIssueModel.status.in_(["identified", "fixing"])),
            "fixedIssues": count(CrmIssueModel, CrmIssueModel.status.in_(["fixed", "closed"])),
        }

    # ---- Helpers ----
    def _get_account(self, account_id: str, store_id: Optional[str] = None):
        query = self.session.query(CrmAccountModel).filter(CrmAccountModel.id == account_id)
        if store_id:
            query = query.filter(CrmAccountModel.store_id == store_id)
        return query.first()

    def _latest_visit_id(self, member_id: str, store_id: str):
        if not member_id:
            return None
        visit = self.session.query(CrmVisitModel).filter(
            CrmVisitModel.member_id == member_id,
            CrmVisitModel.store_id == store_id,
            CrmVisitModel.status == 1,
        ).order_by(CrmVisitModel.arrive_at.desc(), CrmVisitModel.create_date.desc()).first()
        return visit.id if visit else None

    def _sync_visit_consumption(self, visit_id: str, amount: Decimal):
        visit = self.session.query(CrmVisitModel).filter(CrmVisitModel.id == visit_id).first()
        if visit:
            visit.consumption_amount = self._decimal(visit.consumption_amount) + self._decimal(amount)
            visit.update_date = datetime.now()

    def _add_transaction(self, account, tx_type, amount, count_change, before, after, visit_id, notes, operator):
        self.session.add(CrmAccountTransactionModel(
            id=generate_id(), account_id=account.id, store_id=account.store_id, member_id=account.member_id,
            transaction_type=tx_type, amount=amount, count_change=count_change,
            balance_before=before, balance_after=after, related_visit_id=visit_id,
            notes=notes, operator=operator,
        ))

    def _touch_member_visit_stats(self, member_id, arrive_at, amount):
        if not member_id:
            return
        member = self.session.query(CrmMemberModel).filter(CrmMemberModel.id == member_id).first()
        if member:
            member.total_visits = (member.total_visits or 0) + 1
            member.total_spent = self._decimal(member.total_spent) + self._decimal(amount)
            if arrive_at and (not member.last_visit_at or arrive_at > member.last_visit_at):
                member.last_visit_at = arrive_at
            member.update_date = datetime.now()

    @staticmethod
    def _suggestion_category(content: str) -> str:
        text = content or ""
        if any(k in text for k in ["冷", "热", "空调", "房间", "环境", "卫生", "水"]):
            return "environment"
        if any(k in text for k in ["态度", "服务", "技师", "沟通"]):
            return "service"
        if any(k in text for k in ["价格", "优惠", "贵", "便宜", "活动"]):
            return "price"
        if any(k in text for k in ["产品", "项目", "效果", "套餐"]):
            return "product"
        return "other"

    @staticmethod
    def _suggestion_tags(content: str) -> list:
        text = content or ""
        tags = []
        mapping = {
            "环境": ["冷", "热", "空调", "房间", "环境"],
            "卫生": ["卫生", "干净", "毛巾"],
            "服务": ["服务", "态度", "沟通", "技师"],
            "价格": ["价格", "优惠", "贵", "活动"],
            "产品": ["产品", "项目", "套餐", "效果"],
            "茶水": ["水", "茶", "饮品"],
        }
        for tag, keywords in mapping.items():
            if any(k in text for k in keywords):
                tags.append(tag)
        return tags or ["其他"]

    @staticmethod
    def _suggestion_priority(content: str) -> str:
        text = content or ""
        if any(k in text for k in ["投诉", "退款", "销卡", "很差"]):
            return "urgent"
        if any(k in text for k in ["不满意", "态度", "卫生", "没效果"]):
            return "high"
        if any(k in text for k in ["建议", "希望", "可以"]):
            return "medium"
        return "low"

    @staticmethod
    def _should_create_issue_for_close(reason: Optional[str]) -> bool:
        text = reason or ""
        return any(k in text for k in ["不满意", "没效果", "态度", "投诉", "退款", "服务", "卫生", "太冷", "太热"])

    @staticmethod
    def _content_hash(content: str) -> str:
        normalized = re.sub(r"\s+", "", content or "").lower()
        normalized = re.sub(r"[，。！？,.!?；;：:]", "", normalized)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _decimal(value) -> Decimal:
        if value is None or value == "":
            return Decimal("0")
        return Decimal(str(value))

    @staticmethod
    def _parse_date(value):
        if not value:
            return None
        if hasattr(value, "year"):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")[:10]).date()

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _json(value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return value
        return value

    def _member_name(self, member_id):
        if not member_id:
            return None
        member = self.session.query(CrmMemberModel).filter(CrmMemberModel.id == member_id).first()
        return member.name if member else None

    def _member_to_dict(self, m):
        return {
            "id": m.id, "storeId": m.store_id, "name": m.name, "phone": m.phone, "gender": m.gender,
            "birthday": str(m.birthday) if m.birthday else None, "wechat": m.wechat, "source": m.source,
            "level": m.level, "tags": self._json(m.tags), "mekaiTags": self._json(m.mekai_tags),
            "beautyConcerns": self._json(m.beauty_concerns), "healthIssues": self._json(m.health_issues),
            "allergies": m.allergies, "servicePreferences": self._json(m.service_preferences), "notes": m.notes,
            "lastVisitAt": str(m.last_visit_at) if m.last_visit_at else None,
            "totalVisits": m.total_visits or 0, "totalSpent": float(m.total_spent or 0), "status": m.status,
            "createDate": str(m.create_date) if m.create_date else None, "updateDate": str(m.update_date) if m.update_date else None,
        }

    def _visit_to_dict(self, v):
        return {
            "id": v.id, "storeId": v.store_id, "memberId": v.member_id, "memberName": self._member_name(v.member_id), "employeeId": v.employee_id,
            "feedbackRecordId": v.feedback_record_id, "sessionId": v.session_id, "deviceMac": v.device_mac,
            "visitType": v.visit_type, "serviceItems": self._json(v.service_items),
            "arriveAt": str(v.arrive_at) if v.arrive_at else None, "leaveAt": str(v.leave_at) if v.leave_at else None,
            "durationMinutes": v.duration_minutes, "satisfaction": v.satisfaction,
            "consumptionAmount": float(v.consumption_amount or 0), "notes": v.notes, "status": v.status,
            "createDate": str(v.create_date) if v.create_date else None,
        }

    def _account_to_dict(self, a):
        return {
            "id": a.id, "storeId": a.store_id, "memberId": a.member_id, "memberName": self._member_name(a.member_id), "accountType": a.account_type,
            "cardName": a.card_name, "totalAmount": float(a.total_amount or 0), "balanceAmount": float(a.balance_amount or 0),
            "totalCount": a.total_count or 0, "balanceCount": a.balance_count or 0,
            "validStart": str(a.valid_start) if a.valid_start else None, "validEnd": str(a.valid_end) if a.valid_end else None,
            "status": a.status, "closedReason": a.closed_reason, "closedAt": str(a.closed_at) if a.closed_at else None,
            "notes": a.notes, "createDate": str(a.create_date) if a.create_date else None,
        }

    def _body_status_to_dict(self, b):
        return {
            "id": b.id, "storeId": b.store_id, "memberId": b.member_id,
            "memberName": self._member_name(b.member_id), "visitId": b.visit_id,
            "memberProductId": b.member_product_id,
            "recordDate": str(b.record_date) if b.record_date else None,
            "weight": float(b.weight) if b.weight is not None else None,
            "waistline": float(b.waistline) if b.waistline is not None else None,
            "painLevel": b.pain_level, "sleepQuality": b.sleep_quality,
            "skinStatus": b.skin_status, "bodyParts": self._json(b.body_parts),
            "metrics": self._json(b.metrics), "notes": b.notes,
            "createDate": str(b.create_date) if b.create_date else None,
        }

    def _product_to_dict(self, p):
        return {
            "id": p.id, "storeId": p.store_id, "productName": p.product_name,
            "productType": p.product_type, "category": p.category,
            "price": float(p.price or 0), "defaultCount": p.default_count or 0,
            "description": p.description, "status": p.status,
            "createDate": str(p.create_date) if p.create_date else None,
        }

    def _member_product_to_dict(self, p):
        product = self.session.query(CrmProductModel).filter(CrmProductModel.id == p.product_id).first() if p.product_id else None
        return {
            "id": p.id, "storeId": p.store_id, "memberId": p.member_id,
            "memberName": self._member_name(p.member_id), "productId": p.product_id,
            "accountId": p.account_id, "productName": p.product_name,
            "unitPrice": float(p.unit_price or 0), "purchaseCount": p.purchase_count or 0,
            "discount": float(p.discount or 1), "durationMinutes": product.duration_minutes if product else 60,
            "packageItems": self._json(p.package_items), "totalCount": p.total_count or 0,
            "balanceCount": p.balance_count or 0, "totalAmount": float(p.total_amount or 0),
            "balanceAmount": float(p.balance_amount or 0),
            "validStart": str(p.valid_start) if p.valid_start else None,
            "validEnd": str(p.valid_end) if p.valid_end else None,
            "status": p.status, "notes": p.notes,
            "createDate": str(p.create_date) if p.create_date else None,
        }

    def _product_consume_to_dict(self, c):
        return {
            "id": c.id, "storeId": c.store_id, "memberId": c.member_id,
            "memberName": self._member_name(c.member_id), "memberProductId": c.member_product_id,
            "productId": c.product_id, "visitId": c.visit_id,
            "consumeCount": c.consume_count or 0, "consumeAmount": float(c.consume_amount or 0),
            "balanceCountAfter": c.balance_count_after or 0,
            "balanceAmountAfter": float(c.balance_amount_after or 0),
            "notes": c.notes, "operator": c.operator,
            "createDate": str(c.create_date) if c.create_date else None,
        }

    def _transaction_to_dict(self, t):
        return {
            "id": t.id, "accountId": t.account_id, "storeId": t.store_id,
            "memberId": t.member_id, "memberName": self._member_name(t.member_id),
            "transactionType": t.transaction_type, "amount": float(t.amount or 0),
            "countChange": t.count_change or 0, "balanceBefore": float(t.balance_before or 0),
            "balanceAfter": float(t.balance_after or 0), "relatedVisitId": t.related_visit_id,
            "notes": t.notes, "operator": t.operator,
            "createDate": str(t.create_date) if t.create_date else None,
        }

    def _card_close_to_dict(self, c):
        return {
            "id": c.id, "storeId": c.store_id, "memberId": c.member_id, "memberName": self._member_name(c.member_id), "accountId": c.account_id,
            "feedbackRecordId": c.feedback_record_id, "closeType": c.close_type, "reason": c.reason,
            "refundAmount": float(c.refund_amount or 0), "remainingCount": c.remaining_count or 0,
            "status": c.status, "handledBy": c.handled_by, "approvedBy": c.approved_by,
            "handleNotes": c.handle_notes, "createDate": str(c.create_date) if c.create_date else None,
        }

    def _suggestion_to_dict(self, s):
        return {
            "id": s.id, "storeId": s.store_id, "feedbackRecordId": s.feedback_record_id, "memberId": s.member_id,
            "content": s.content, "category": s.category, "tags": self._json(s.tags),
            "priority": s.priority, "source": s.source, "submitterName": s.submitter_name,
            "memberName": self._member_name(s.member_id),
            "duplicateGroupId": s.duplicate_group_id,
            "frequency": s.frequency or 1, "status": s.status, "adoptedAt": str(s.adopted_at) if s.adopted_at else None,
            "rejectedReason": s.rejected_reason, "handledBy": s.handled_by, "handleNotes": s.handle_notes,
            "createDate": str(s.create_date) if s.create_date else None,
        }

    def _issue_to_dict(self, i):
        return {
            "id": i.id, "storeId": i.store_id, "feedbackRecordId": i.feedback_record_id, "memberId": i.member_id,
            "cardCloseId": i.card_close_id, "title": i.title, "description": i.description,
            "severity": i.severity, "category": i.category, "status": i.status,
            "identifiedAt": str(i.identified_at) if i.identified_at else None,
            "fixPlan": i.fix_plan, "fixDeadline": str(i.fix_deadline) if i.fix_deadline else None,
            "fixedAt": str(i.fixed_at) if i.fixed_at else None, "fixResult": i.fix_result,
            "assignedTo": i.assigned_to, "closedAt": str(i.closed_at) if i.closed_at else None,
            "createDate": str(i.create_date) if i.create_date else None,
        }

    def _feedback_to_dict(self, r):
        return {
            "id": r.id, "storeId": r.store_id, "memberId": r.member_id, "visitId": r.visit_id,
            "cardCloseId": r.card_close_id, "satisfaction": r.satisfaction,
            "rawAsrText": r.raw_asr_text, "cleanedText": r.cleaned_text,
            "qaJson": r.qa_json, "reviewLong": r.review_long, "reviewShort": r.review_short,
            "createDate": str(r.create_date) if r.create_date else None,
        }
