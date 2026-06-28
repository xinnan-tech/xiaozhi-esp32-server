"""CRM 用户故事自动化测试。

用户故事：
店长希望客户完成语音反馈后，系统能按手机号后四位识别客户，自动把反馈、到店、
满意度、建议、问题修复、账户消费流水串起来，并在统计概览中按员工展示好评、
中评、差评 KPI；同时客户档案支持麦凯66字段，方便门店持续经营客户关系。
"""

import asyncio
import unittest
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.application.crm_service import CrmService
from app.application.feedback_service import FeedbackService
from app.application.stats_service import StatsService
from app.infrastructure.persistence.database import Base
from app.infrastructure.persistence.models import (
    CrmIssueModel,
    CrmMemberModel,
    CrmSuggestionModel,
    CrmVisitModel,
    EmployeeModel,
    FeedbackRecordModel,
    StoreModel,
)
from app.shared.mekai66 import MEKAI66_FIELDS
from app.shared.utils import generate_id


class CrmStoryTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        self.crm = CrmService(self.session)
        self.stats = StatsService(self.session)
        self.feedback = FeedbackService(self.session)
        self.store = StoreModel(id="store001", store_code="558744", store_name="测试门店", status=1)
        self.emp = EmployeeModel(id="emp001", name="小王", number=1, store_id="store001", status=1)
        self.session.add_all([self.store, self.emp])
        self.session.commit()

    async def asyncTearDown(self):
        self.session.close()
        self.engine.dispose()

    async def _member(self):
        return await self.crm.create_member({
            "store_id": "store001",
            "name": "张女士",
            "phone": "13800001234",
            "beautyConcerns": ["皮肤干燥"],
            "healthIssues": ["肩颈酸痛"],
            "mekaiTags": {"nickname": "张姐", "preferred_employee": "小王"},
        }, "tester")

    async def _account_with_visit(self):
        member = await self._member()
        visit = await self.crm.create_visit({
            "store_id": "store001",
            "memberId": member["id"],
            "employeeId": "emp001",
            "arriveAt": "2026-06-18T10:00:00",
            "serviceItems": ["肩颈调理"],
        }, "tester")
        account = await self.crm.create_account({
            "store_id": "store001",
            "memberId": member["id"],
            "cardName": "肩颈10次卡",
            "accountType": "count",
            "totalAmount": 1000,
            "totalCount": 10,
        }, "tester")
        return member, visit, account

    def _record(self, satisfaction="satisfied", employee_id="emp001", member_id=None):
        record = FeedbackRecordModel(
            id=generate_id(), store_id="store001", employee_id=employee_id,
            member_id=member_id, satisfaction=satisfaction, review_long="测试评价",
            cleaned_text="客户反馈房间有点冷，手机号后四位1234", create_date=datetime.now(),
        )
        self.session.add(record)
        self.session.commit()
        return record

    async def test_01_mekai66_has_exactly_66_fields(self):
        self.assertEqual(66, len(MEKAI66_FIELDS))

    async def test_02_mekai66_keys_are_unique(self):
        keys = [f["key"] for f in MEKAI66_FIELDS]
        self.assertEqual(len(keys), len(set(keys)))

    async def test_03_create_member_with_mekai66(self):
        member = await self._member()
        self.assertEqual("张女士", member["name"])
        self.assertEqual("张姐", member["mekaiTags"]["nickname"])

    async def test_04_search_member_by_phone(self):
        await self._member()
        result = await self.crm.list_members(store_id="store001", keyword="1234")
        self.assertEqual(1, result["total"])

    async def test_05_update_member_health_profile(self):
        member = await self._member()
        updated = await self.crm.update_member(member["id"], {"healthIssues": ["腰背酸痛"]}, "store001", "tester")
        self.assertIn("腰背酸痛", updated["healthIssues"])

    async def test_06_create_visit_calculates_duration(self):
        member = await self._member()
        visit = await self.crm.create_visit({"store_id": "store001", "memberId": member["id"], "arriveAt": "2026-06-18T10:00:00", "leaveAt": "2026-06-18T11:30:00"}, "tester")
        self.assertEqual(90, visit["durationMinutes"])

    async def test_07_visit_returns_member_name(self):
        member, visit, _ = await self._account_with_visit()
        self.assertEqual(member["name"], visit["memberName"])

    async def test_08_visit_updates_member_stats(self):
        member, _, _ = await self._account_with_visit()
        detail = await self.crm.get_member(member["id"], "store001")
        self.assertEqual(1, detail["totalVisits"])

    async def test_09_create_account_creates_recharge_transaction(self):
        member, _, account = await self._account_with_visit()
        txs = await self.crm.list_account_transactions(member_id=member["id"])
        self.assertEqual(1, txs["total"])
        self.assertEqual("recharge", txs["list"][0]["transactionType"])

    async def test_10_consume_account_decreases_count(self):
        _, _, account = await self._account_with_visit()
        consumed = await self.crm.consume_account(account["id"], {"countChange": 1}, "store001", "tester")
        self.assertEqual(9, consumed["balanceCount"])

    async def test_11_consume_account_creates_consume_transaction(self):
        member, _, account = await self._account_with_visit()
        await self.crm.consume_account(account["id"], {"countChange": 1, "notes": "消费1次"}, "store001", "tester")
        txs = await self.crm.list_account_transactions(member_id=member["id"])
        self.assertEqual(2, txs["total"])
        self.assertEqual("consume", txs["list"][0]["transactionType"])

    async def test_12_consume_without_visit_links_latest_visit(self):
        _, visit, account = await self._account_with_visit()
        await self.crm.consume_account(account["id"], {"amount": 88, "countChange": 1}, "store001", "tester")
        txs = await self.crm.list_account_transactions(account_id=account["id"])
        consume = [t for t in txs["list"] if t["transactionType"] == "consume"][0]
        self.assertEqual(visit["id"], consume["relatedVisitId"])

    async def test_13_consume_syncs_visit_amount(self):
        member, _, account = await self._account_with_visit()
        await self.crm.consume_account(account["id"], {"amount": 88, "countChange": 1}, "store001", "tester")
        detail = await self.crm.get_member(member["id"], "store001")
        self.assertEqual(88.0, detail["visits"][0]["consumptionAmount"])

    async def test_14_create_suggestion(self):
        member = await self._member()
        suggestion = await self.crm.create_suggestion({"store_id": "store001", "memberId": member["id"], "content": "房间有点冷"}, "tester")
        self.assertEqual("pending", suggestion["status"])

    async def test_15_duplicate_suggestion_increments_frequency(self):
        await self.crm.create_suggestion({"store_id": "store001", "content": "房间有点冷"}, "tester")
        suggestion = await self.crm.create_suggestion({"store_id": "store001", "content": "房间有点冷"}, "tester")
        self.assertEqual(2, suggestion["frequency"])

    async def test_16_adopt_suggestion_with_notes(self):
        suggestion = await self.crm.create_suggestion({"store_id": "store001", "content": "提前开空调"}, "tester")
        adopted = await self.crm.update_suggestion_status(suggestion["id"], "adopted", {"handleNotes": "服务前30分钟开空调"}, "store001", "tester")
        self.assertEqual("adopted", adopted["status"])
        self.assertEqual("服务前30分钟开空调", adopted["handleNotes"])

    async def test_17_create_issue(self):
        issue = await self.crm.create_issue({"store_id": "store001", "title": "房间温度偏低"}, "tester")
        self.assertEqual("identified", issue["status"])

    async def test_18_update_issue_to_fixed_sets_fixed_time(self):
        issue = await self.crm.create_issue({"store_id": "store001", "title": "房间温度偏低"}, "tester")
        fixed = await self.crm.update_issue(issue["id"], {"status": "fixed", "fixResult": "已加毛毯"}, "store001", "tester")
        self.assertEqual("fixed", fixed["status"])
        self.assertIsNotNone(fixed["fixedAt"])

    async def test_19_close_card_marks_account_closed(self):
        _, _, account = await self._account_with_visit()
        close = await self.crm.close_card({"accountId": account["id"], "reason": "搬家", "refundAmount": 100}, "store001", "tester")
        self.assertEqual("done", close["status"])
        accounts = await self.crm.list_accounts(store_id="store001", status=0)
        self.assertEqual(1, accounts["total"])

    async def test_20_close_card_bad_reason_does_not_auto_create_issue(self):
        _, _, account = await self._account_with_visit()
        await self.crm.close_card({"accountId": account["id"], "reason": "服务不满意，要求退款", "refundAmount": 100}, "store001", "tester")
        issues = await self.crm.list_issues(store_id="store001")
        self.assertEqual(0, issues["total"])

    async def test_21_bind_feedback_to_member_and_visit(self):
        member, visit, _ = await self._account_with_visit()
        record = self._record()
        bound = await self.crm.bind_feedback(record.id, {"memberId": member["id"], "visitId": visit["id"]}, "store001")
        self.assertEqual(member["id"], bound["memberId"])
        self.assertEqual(visit["id"], bound["visitId"])

    async def test_22_employee_kpi_groups_good_middle_bad(self):
        self._record("very_satisfied")
        self._record("satisfied")
        self._record("unsatisfied")
        self._record("very_bad")
        kpi = await self.stats.get_employee_kpi("store001")
        self.assertEqual(2, kpi[0]["good"])
        self.assertEqual(1, kpi[0]["middle"])
        self.assertEqual(1, kpi[0]["bad"])

    async def test_23_employee_records_filter_bad(self):
        self._record("very_satisfied")
        self._record("very_bad")
        records = await self.stats.get_employee_records("emp001", "store001", "bad")
        self.assertEqual(1, records["total"])
        self.assertEqual("very_bad", records["list"][0]["satisfaction"])

    async def test_24_phone_tail_extraction(self):
        self.assertEqual("1234", self.feedback._extract_phone_tail("我的手机号后四位是1234"))

    async def test_25_auto_link_feedback_finds_member_by_tail(self):
        member = await self._member()
        record = self._record("satisfied")
        qa = "Q3: 客户做了什么项目/服务？ A3: 肩颈调理\nQ4: 客户什么时间到店的？ A4: 10点30\nQ5: 客户之前身体哪里不舒服？ A5: 睡眠不好\nQ8: 客户有什么建议？ A8: 希望提前开空调\nQ9: 客户手机号后四位是多少？ A9: 1234"
        entity = await self.feedback.record_repo.get_by_id(record.id)
        self.feedback._auto_link_feedback_to_crm(entity, record.cleaned_text, qa, "satisfied")
        updated = self.session.query(FeedbackRecordModel).filter(FeedbackRecordModel.id == record.id).first()
        self.assertEqual(member["id"], updated.member_id)

    async def test_26_auto_link_feedback_creates_visit(self):
        await self._member()
        record = self._record("satisfied")
        entity = await self.feedback.record_repo.get_by_id(record.id)
        qa = "Q3: 客户做了什么项目/服务？ A3: 肩颈调理\nQ4: 客户什么时间到店的？ A4: 10点30\nQ9: 客户手机号后四位是多少？ A9: 1234"
        self.feedback._auto_link_feedback_to_crm(entity, record.cleaned_text, qa, "satisfied")
        self.assertEqual(1, self.session.query(CrmVisitModel).count())

    async def test_27_auto_link_feedback_creates_suggestion(self):
        await self._member()
        record = self._record("satisfied")
        entity = await self.feedback.record_repo.get_by_id(record.id)
        qa = "Q8: 客户有什么建议？ A8: 希望提前开空调\nQ9: 客户手机号后四位是多少？ A9: 1234"
        self.feedback._auto_link_feedback_to_crm(entity, record.cleaned_text, qa, "satisfied")
        self.assertEqual(1, self.session.query(CrmSuggestionModel).count())

    async def test_28_auto_link_feedback_no_longer_creates_issue_for_bad_feedback(self):
        await self._member()
        record = self._record("very_bad")
        entity = await self.feedback.record_repo.get_by_id(record.id)
        qa = "Q9: 客户手机号后四位是多少？ A9: 1234"
        self.feedback._auto_link_feedback_to_crm(entity, "客户很差，要求退款", qa, "very_bad")
        self.assertEqual(0, self.session.query(CrmIssueModel).count())

    async def test_29_member_detail_aggregates_related_data(self):
        member, _, account = await self._account_with_visit()
        await self.crm.consume_account(account["id"], {"countChange": 1}, "store001", "tester")
        await self.crm.create_suggestion({"store_id": "store001", "memberId": member["id"], "content": "建议"}, "tester")
        await self.crm.create_issue({"store_id": "store001", "memberId": member["id"], "title": "问题"}, "tester")
        detail = await self.crm.get_member(member["id"], "store001")
        self.assertTrue(detail["visits"])
        self.assertTrue(detail["accounts"])
        self.assertTrue(detail["transactions"])
        self.assertTrue(detail["suggestions"])
        self.assertTrue(detail["issues"])

    async def test_30_crm_overview_counts_all_modules(self):
        member, _, account = await self._account_with_visit()
        await self.crm.create_suggestion({"store_id": "store001", "memberId": member["id"], "content": "建议"}, "tester")
        await self.crm.create_issue({"store_id": "store001", "memberId": member["id"], "title": "问题"}, "tester")
        await self.crm.close_card({"accountId": account["id"], "reason": "搬家"}, "store001", "tester")
        overview = await self.crm.get_overview("store001")
        self.assertEqual(1, overview["members"])
        self.assertEqual(1, overview["visits"])
        self.assertEqual(1, overview["cardCloses"])
        self.assertEqual(1, overview["pendingSuggestions"])
        self.assertEqual(1, overview["openIssues"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
