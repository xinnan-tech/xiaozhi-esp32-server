"""
LLM 客户端基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class LLMClient(ABC):
    """LLM 客户端基类"""

    @abstractmethod
    async def extract_facts(
        self,
        conversation: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        从对话中提取事实

        Args:
            conversation: 对话文本
            context: 上下文信息
                - current_date: 当前日期
                - observation_date: 观察日期（用于解析相对时间）
                - recently_extracted: 最近提取的记忆（用于去重）
                - existing_memories: 现有相关记忆

        Returns:
            [{"content": "...", "type": "FACT|INTENTION|PREFERENCE", ...}]
        """
        pass
