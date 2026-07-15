"""实时安全告警纯逻辑单测（无重型依赖，可直接 python -m pytest 运行）"""

import unittest

from core.providers.memory.aipet.safety_rules import (
    danger_level_ok,
    emotion_abnormal,
    in_cooldown,
)


class TestSafetyRules(unittest.TestCase):
    def test_danger_level_threshold(self):
        # 仅 medium 及以上才上报
        self.assertFalse(danger_level_ok("low", "medium"))
        self.assertTrue(danger_level_ok("medium", "medium"))
        self.assertTrue(danger_level_ok("high", "medium"))
        self.assertTrue(danger_level_ok("critical", "medium"))
        # 未知等级按 medium 处理，避免漏报
        self.assertTrue(danger_level_ok("weird", "medium"))
        # 大小写不敏感
        self.assertTrue(danger_level_ok("CRITICAL", "medium"))

    def test_emotion_abnormal(self):
        abnormal = ["fear", "sad", "angry"]
        self.assertTrue(emotion_abnormal("fear", abnormal))
        self.assertTrue(emotion_abnormal("SAD", abnormal))  # 大小写不敏感
        self.assertFalse(emotion_abnormal("happy", abnormal))
        self.assertFalse(emotion_abnormal("neutral", abnormal))
        # 空集合 → 任何情绪都不视为异常
        self.assertFalse(emotion_abnormal("fear", []))

    def test_in_cooldown(self):
        now = 1000.0
        self.assertTrue(in_cooldown(990.0, now, 60))   # 冷却中
        self.assertFalse(in_cooldown(900.0, now, 60))  # 已过期
        self.assertFalse(in_cooldown(None, now, 60))   # 从未推送


if __name__ == "__main__":
    unittest.main()
