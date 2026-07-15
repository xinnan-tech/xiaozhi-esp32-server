"""实时安全告警的纯判定逻辑（无副作用、易单测）。

- 危险等级阈值：低于 min_level 不上报，抑制误报疲劳
- 异常情绪集合：仅集合内情绪才通知家长
- 冷却去重：同类型在冷却期内不重复推送
"""

# 危险等级排序（数值越大越严重）
DANGER_LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def danger_level_ok(level: str, min_level: str = "medium") -> bool:
    """危险等级是否达到上报阈值"""
    return DANGER_LEVEL_ORDER.get((level or "").lower(), 1) >= DANGER_LEVEL_ORDER.get(
        min_level, 1
    )


def emotion_abnormal(level: str, abnormal_emotions) -> bool:
    """情绪类型是否属于需通知的异常集合（大小写不敏感）"""
    abnormal = {(e or "").lower() for e in (abnormal_emotions or [])}
    return (level or "").lower() in abnormal


def in_cooldown(last_ts, now, cooldown_seconds: int) -> bool:
    """是否仍处于冷却期（同类型不重复推送）"""
    return last_ts is not None and (now - last_ts) < cooldown_seconds
