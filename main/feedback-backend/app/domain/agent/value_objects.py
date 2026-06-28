"""智能体配置值对象"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class DialogueConfig:
    """对话配置值对象"""
    rounds: int = 7
    questions: Optional[tuple] = None  # 使用 tuple 保证不可变

    def __post_init__(self):
        if self.rounds < 1 or self.rounds > 20:
            raise ValueError(f"对话轮次必须在 1-20 之间，当前值: {self.rounds}")

    def get_questions(self) -> List[str]:
        """获取前 N 个问题"""
        if not self.questions:
            return []
        return list(self.questions[:self.rounds])


@dataclass(frozen=True)
class LLMProviderConfig:
    """LLM 提供商配置值对象"""
    provider: str
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None

    def is_valid(self) -> bool:
        return bool(self.provider and self.api_key)
