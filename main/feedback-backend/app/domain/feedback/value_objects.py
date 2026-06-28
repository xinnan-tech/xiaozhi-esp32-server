"""反馈值对象"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Satisfaction:
    """满意度值对象"""
    level: str  # very_satisfied / satisfied / unsatisfied / very_bad

    VALID_LEVELS = {"very_satisfied", "satisfied", "unsatisfied", "very_bad"}

    def __post_init__(self):
        if self.level not in self.VALID_LEVELS:
            raise ValueError(f"无效的满意度等级: {self.level}")

    @property
    def text(self) -> str:
        mapping = {
            "very_satisfied": "非常满意",
            "satisfied": "满意",
            "unsatisfied": "不满意",
            "very_bad": "很差",
        }
        return mapping.get(self.level, "未知")

    @property
    def score(self) -> int:
        mapping = {
            "very_satisfied": 4,
            "satisfied": 3,
            "unsatisfied": 2,
            "very_bad": 1,
        }
        return mapping.get(self.level, 0)

    @property
    def is_positive(self) -> bool:
        return self.level in ("very_satisfied", "satisfied")

    def __str__(self) -> str:
        return self.level


@dataclass(frozen=True)
class ReviewContent:
    """点评内容值对象"""
    long_review: Optional[str] = None   # 标准版
    short_review: Optional[str] = None  # 精简版

    @property
    def has_content(self) -> bool:
        return bool(self.long_review or self.short_review)
