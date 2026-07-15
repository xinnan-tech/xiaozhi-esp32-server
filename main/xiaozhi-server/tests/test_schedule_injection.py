"""
日程注入提示词 - 单元测试

覆盖本次改动：
1. dialogue.py: get_llm_dialogue_with_memory 注入 schedule_str 到半稳定 system 段
2. aipet.py: get_today_schedule() 格式化逻辑
3. base.py: get_today_schedule() 默认实现

运行：python3 -m unittest tests.test_schedule_injection -v
"""
import os
import sys
import unittest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

# 将 xiaozhi-server 加入路径，使 core.* 可导入
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from core.utils.dialogue import Dialogue, Message
from core.providers.memory.aipet.aipet import MemoryProvider
from core.providers.memory.base import MemoryProviderBase


def _build_dialogue():
    """构造一个含 <context> 分界点和 <memory> 占位的对话"""
    d = Dialogue()
    d.put(Message(
        role="system",
        content=("你是小智\n"
                 "<context>\n"
                 "- 今天日期：2026-06-17\n"
                 "- 当前时间：10:00\n"
                 "</context>\n"
                 "<memory>\n</memory>")
    ))
    d.put(Message(role="user", content="你好"))
    d.put(Message(role="assistant", content="你好啊"))
    return d


class TestDialogueScheduleInjection(unittest.TestCase):
    """日程应注入到半稳定 system 段（③），而非实时 user 段（④）"""

    def test_schedule_injected_into_system_role(self):
        """日程注入的消息必须是 system 角色（半稳定段）"""
        d = _build_dialogue()
        msgs = d.get_llm_dialogue_with_memory(
            memory_str="- 用户喜欢喝咖啡",
            schedule_str="- 今天 15:00：开产品评审会"
        )
        schedule_msgs = [m for m in msgs if "<schedule>" in m["content"]]
        self.assertEqual(len(schedule_msgs), 1)
        self.assertEqual(schedule_msgs[0]["role"], "system")
        self.assertIn("开产品评审会", schedule_msgs[0]["content"])

    def test_schedule_not_in_user_segment(self):
        """日程不应泄漏到 user 段"""
        d = _build_dialogue()
        msgs = d.get_llm_dialogue_with_memory(schedule_str="- 开会")
        for m in msgs:
            if m["role"] == "user":
                self.assertNotIn("<schedule>", m["content"])

    def test_schedule_tag_survives_memory_cleanup(self):
        """<schedule> 标签不被清理 <memory> 的正则误删"""
        d = _build_dialogue()
        msgs = d.get_llm_dialogue_with_memory(schedule_str="- 开会")
        all_content = "\n".join(m["content"] for m in msgs)
        self.assertIn("<schedule>", all_content)
        self.assertIn("</schedule>", all_content)

    def test_memory_still_in_realtime_user(self):
        """回归：记忆仍注入实时 user 段"""
        d = _build_dialogue()
        msgs = d.get_llm_dialogue_with_memory(memory_str="- 我喜欢咖啡")
        memory_msgs = [m for m in msgs if "<memory>" in m["content"]]
        self.assertEqual(len(memory_msgs), 1)
        self.assertEqual(memory_msgs[0]["role"], "user")
        self.assertIn("咖啡", memory_msgs[0]["content"])

    def test_empty_schedule_not_injected(self):
        """空日程不产生 <schedule> 块"""
        d = _build_dialogue()
        msgs = d.get_llm_dialogue_with_memory(schedule_str="")
        all_content = "\n".join(m["content"] for m in msgs)
        self.assertNotIn("<schedule>", all_content)

    def test_none_schedule_backward_compatible(self):
        """不传 schedule_str 时向后兼容，行为不变"""
        d = _build_dialogue()
        msgs = d.get_llm_dialogue_with_memory(memory_str="- 咖啡")
        all_content = "\n".join(m["content"] for m in msgs)
        self.assertNotIn("<schedule>", all_content)
        self.assertIn("咖啡", all_content)

    def test_schedule_and_memory_coexist(self):
        """日程（system）与记忆（user）同时注入且互不干扰"""
        d = _build_dialogue()
        msgs = d.get_llm_dialogue_with_memory(
            memory_str="- 我喜欢咖啡",
            schedule_str="- 今天 15:00：开会"
        )
        has_schedule_system = any(
            m["role"] == "system" and "<schedule>" in m["content"] for m in msgs
        )
        has_memory_user = any(
            m["role"] == "user" and "<memory>" in m["content"] for m in msgs
        )
        self.assertTrue(has_schedule_system)
        self.assertTrue(has_memory_user)


def _mock_intention(content, time_description=None, planned_time=None):
    return MagicMock(content=content,
                     time_description=time_description,
                     planned_time=planned_time)


def _make_provider(intentions=None, manager_exists=True, role_id="device123",
                   milestone=None):
    """绕过 __init__ 构造 MemoryProvider，注入 mock manager"""
    p = MemoryProvider.__new__(MemoryProvider)
    p.role_id = role_id
    if manager_exists:
        p.manager = MagicMock()
        p.manager.get_upcoming_intentions = AsyncMock(return_value=intentions or [])
        p.manager.get_relationship_milestone = AsyncMock(return_value=milestone)
        p.manager.get_annual_events_in_range = AsyncMock(return_value=[])
        p.manager.record_first_meeting = AsyncMock(return_value=1)
    else:
        p.manager = None
    return p


class TestFormatWhen(unittest.TestCase):
    """_format_when 时间锚点格式化（缓解幻觉：绝对日期优先，方括号锚点）"""
    TODAY = date(2026, 6, 17)

    def test_today(self):
        r = MemoryProvider._format_when(datetime(2026, 6, 17, 15, 0), None, self.TODAY)
        self.assertEqual(r, "[06-17 今天 15:00]")

    def test_tomorrow(self):
        r = MemoryProvider._format_when(datetime(2026, 6, 18, 10, 0), None, self.TODAY)
        self.assertEqual(r, "[06-18 明天 10:00]")

    def test_day_after_tomorrow(self):
        r = MemoryProvider._format_when(datetime(2026, 6, 19, 9, 0), None, self.TODAY)
        self.assertEqual(r, "[06-19 后天 09:00]")

    def test_n_days_later(self):
        r = MemoryProvider._format_when(datetime(2026, 6, 23, 9, 0), None, self.TODAY)
        self.assertEqual(r, "[06-23 6天后 09:00]")

    def test_planned_time_preferred_over_description(self):
        """绝对时间优先于相对描述，降低多条日程的时间混淆"""
        r = MemoryProvider._format_when(datetime(2026, 6, 17, 15, 0), "下周", self.TODAY)
        self.assertEqual(r, "[06-17 今天 15:00]")

    def test_only_description(self):
        r = MemoryProvider._format_when(None, "下周三", self.TODAY)
        self.assertEqual(r, "[下周三]")

    def test_no_time_fallback(self):
        r = MemoryProvider._format_when(None, None, self.TODAY)
        self.assertEqual(r, "[近期]")


class TestGetTodaySchedule(unittest.IsolatedAsyncioTestCase):
    """aipet.py get_today_schedule() 集成逻辑"""

    async def test_empty_intentions_returns_empty(self):
        """空意图列表返回空串"""
        p = _make_provider([])
        result = await p.get_today_schedule()
        self.assertEqual(result, "")

    async def test_no_manager_returns_empty(self):
        """无 manager 安全返回空串，不抛异常"""
        p = _make_provider(manager_exists=False)
        result = await p.get_today_schedule()
        self.assertEqual(result, "")

    async def test_calls_upcoming_intentions_with_correct_args(self):
        """调用 get_upcoming_intentions 时 days=7（扩大窗口）且传入 role_id"""
        p = _make_provider([])
        await p.get_today_schedule()
        p.manager.get_upcoming_intentions.assert_awaited_once_with(
            device_id="device123", user_id=None, days=7
        )
        p.manager.get_annual_events_in_range.assert_awaited_once_with(
            device_id="device123", user_id=None, days=7
        )

    async def test_multiple_intentions_all_have_anchors(self):
        """多条日程每条都带方括号时间锚点"""
        intentions = [
            _mock_intention("开会", planned_time=datetime(2026, 6, 17, 15, 0)),
            _mock_intention("出差", planned_time=datetime(2026, 6, 19, 9, 0)),
            _mock_intention("买牛奶"),
        ]
        p = _make_provider(intentions)
        result = await p.get_today_schedule()
        # 今日计划 header (1) + 3 条日程 (3) = 4 行
        self.assertEqual(len(result.strip().split("\n")), 4)
        self.assertEqual(result.count("["), 3)  # 每条一个方括号锚点
        self.assertEqual(result.count("]"), 3)
        self.assertIn("开会", result)
        self.assertIn("买牛奶", result)


class _ConcreteProvider(MemoryProviderBase):
    """最小具体子类，用于测试基类默认实现"""
    async def save_memory(self, msgs, session_id=None):
        pass

    async def query_memory(self, query: str) -> str:
        return ""


class TestBaseProviderDefault(unittest.IsolatedAsyncioTestCase):
    """base.py 默认实现，保证其他 provider 不受影响"""

    async def test_base_default_returns_empty(self):
        """基类默认 get_today_schedule 返回空串"""
        base = _ConcreteProvider.__new__(_ConcreteProvider)
        result = await base.get_today_schedule()
        self.assertEqual(result, "")

    async def test_base_default_record_first_meeting_noop(self):
        """基类默认 record_first_meeting 不抛异常"""
        base = _ConcreteProvider.__new__(_ConcreteProvider)
        await base.record_first_meeting()  # 不应报错


class TestMilestoneInjection(unittest.IsolatedAsyncioTestCase):
    """关系里程碑注入 get_today_schedule"""

    async def test_milestone_none_not_injected(self):
        """里程碑为 None 时不注入'关系提醒'段"""
        p = _make_provider(milestone=None)
        result = await p.get_today_schedule()
        self.assertNotIn("关系提醒", result)

    async def test_milestone_injected(self):
        """里程碑有值时出现在结果中"""
        p = _make_provider(
            intentions=[_mock_intention("开会", planned_time=datetime(2026, 6, 17, 15, 0))],
            milestone="今天是你和用户认识的第 30 天",
        )
        result = await p.get_today_schedule()
        self.assertIn("关系提醒", result)
        self.assertIn("第 30 天", result)

    async def test_milestone_only_no_intentions(self):
        """无日程但有里程碑时仍注入"""
        p = _make_provider(intentions=[], milestone="今天是我们第一次见面")
        result = await p.get_today_schedule()
        self.assertIn("关系提醒", result)
        self.assertIn("第一次见面", result)

    async def test_milestone_exception_safe(self):
        """get_relationship_milestone 抛异常时不影响日程注入"""
        p = _make_provider(intentions=[
            _mock_intention("开会", planned_time=datetime(2026, 6, 17, 15, 0))
        ])
        p.manager.get_relationship_milestone = AsyncMock(
            side_effect=Exception("DB error")
        )
        result = await p.get_today_schedule()
        self.assertIn("开会", result)
        self.assertNotIn("关系提醒", result)


class TestRecordFirstMeeting(unittest.IsolatedAsyncioTestCase):
    """record_first_meeting 透传逻辑"""

    async def test_calls_manager_record_first_meeting(self):
        """有 manager 和 role_id 时透传至 manager"""
        p = _make_provider()
        await p.record_first_meeting()
        p.manager.record_first_meeting.assert_awaited_once_with("device123")

    async def test_no_manager_safe(self):
        """无 manager 时安全返回不报错"""
        p = _make_provider(manager_exists=False)
        await p.record_first_meeting()  # 不应抛异常

    async def test_no_role_id_safe(self):
        """无 role_id 时安全返回"""
        p = _make_provider()
        p.role_id = None
        await p.record_first_meeting()  # 不应抛异常

    async def test_exception_logged_not_raised(self):
        """manager 抛异常时不向上传播"""
        p = _make_provider()
        p.manager.record_first_meeting = AsyncMock(
            side_effect=Exception("DB error")
        )
        await p.record_first_meeting()  # 不应抛异常


class TestAnnualEventsInjection(unittest.IsolatedAsyncioTestCase):
    """年重复事件（生日/纪念日）注入 get_today_schedule（aipet 层）"""

    async def test_no_annual_no_section(self):
        """无年重复事件时不注入'纪念日提醒'段"""
        p = _make_provider(
            intentions=[_mock_intention("开会", planned_time=datetime(2026, 6, 17, 15, 0))],
            milestone=None,
        )
        p.manager.get_annual_events_in_range = AsyncMock(return_value=[])
        result = await p.get_today_schedule()
        self.assertNotIn("纪念日提醒", result)
        self.assertIn("开会", result)

    async def test_annual_injected_this_week(self):
        """本周生日被投影并注入独立'纪念日提醒'段"""
        birthday = _mock_intention(
            "用户的生日",
            time_description="每年7月20日",
            planned_time=datetime(2026, 7, 20, 9, 0),
        )
        p = _make_provider(
            intentions=[_mock_intention("开会", planned_time=datetime(2026, 6, 17, 15, 0))],
            milestone=None,
        )
        p.manager.get_annual_events_in_range = AsyncMock(return_value=[birthday])
        result = await p.get_today_schedule()
        self.assertIn("纪念日提醒", result)
        self.assertIn("07-20", result)
        self.assertIn("用户的生日", result)

    async def test_annual_exception_safe(self):
        """get_annual_events_in_range 抛异常时不影响普通日程注入"""
        p = _make_provider(
            intentions=[_mock_intention("开会", planned_time=datetime(2026, 6, 17, 15, 0))],
            milestone=None,
        )
        p.manager.get_annual_events_in_range = AsyncMock(
            side_effect=Exception("DB error")
        )
        result = await p.get_today_schedule()
        self.assertIn("开会", result)
        self.assertNotIn("纪念日提醒", result)


class TestAnnualEventsManager(unittest.IsolatedAsyncioTestCase):
    """manager 层 get_annual_events_in_range 投影逻辑（用固定 now，不依赖真实日期）"""

    def _make_manager(self, memories):
        from xiaozhi_memory.core.memory_manager import MemoryManager
        from unittest.mock import MagicMock
        mgr = MemoryManager.__new__(MemoryManager)
        mgr.store = MagicMock()
        mgr.store.get_by_device = MagicMock(return_value=memories)
        return mgr

    def _birthday(self, desc, planned, content="用户的生日"):
        from xiaozhi_memory.core.memory_manager import IntentionMemory
        return IntentionMemory(
            id="b1", device_id="d", user_id=None, content=content,
            intention_type="birthday", time_description=desc, planned_time=planned,
        )

    def _meeting(self, planned):
        from xiaozhi_memory.core.memory_manager import IntentionMemory
        return IntentionMemory(
            id="m1", device_id="d", user_id=None, content="开会",
            intention_type="meeting", planned_time=planned,
        )

    async def test_this_year_projection(self):
        """本年生日落在 7 天窗口内 → 投影到本年"""
        mgr = self._make_manager([self._birthday("每年7月20日", datetime(2026, 7, 20, 9, 0))])
        events = await mgr.get_annual_events_in_range("d", days=7, now=datetime(2026, 7, 15, 10, 0))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].planned_time, datetime(2026, 7, 20, 9, 0))
        self.assertEqual(events[0].intention_type, "birthday")

    async def test_past_this_year_projected_to_next_year(self):
        """本年生日已过 → 投影到明年返回（窗口跨年）"""
        mgr = self._make_manager([self._birthday("每年1月5日", datetime(2026, 1, 5, 9, 0))])
        # now=12-30，窗口 7 天 → 到明年 1-6，命中明年 1-5
        events = await mgr.get_annual_events_in_range("d", days=7, now=datetime(2026, 12, 30, 10, 0))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].planned_time, datetime(2027, 1, 5, 9, 0))

    async def test_filter_non_annual(self):
        """一次性会议（meeting）不被当作年重复事件"""
        mgr = self._make_manager([self._meeting(datetime(2026, 7, 20, 9, 0))])
        events = await mgr.get_annual_events_in_range("d", days=7, now=datetime(2026, 7, 15, 10, 0))
        self.assertEqual(events, [])

    async def test_leap_day_safe_in_common_year(self):
        """2/29 生日在平年不报错、不误提醒"""
        mgr = self._make_manager([self._birthday("每年2月29日", datetime(2024, 2, 29, 9, 0))])
        events = await mgr.get_annual_events_in_range("d", days=7, now=datetime(2025, 2, 25, 10, 0))
        self.assertEqual(events, [])

    async def test_leap_day_hit_in_leap_year(self):
        """2/29 生日在闰年正常命中"""
        mgr = self._make_manager([self._birthday("每年2月29日", datetime(2024, 2, 29, 9, 0))])
        events = await mgr.get_annual_events_in_range("d", days=7, now=datetime(2024, 2, 25, 10, 0))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].planned_time, datetime(2024, 2, 29, 9, 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
