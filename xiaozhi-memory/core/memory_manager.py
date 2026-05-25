"""
核心记忆管理器
"""
import asyncio
import re
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum

from memories.base import (
    BaseMemory, FactMemory, IntentionMemory, PreferenceMemory,
    MemoryType, IntentionStatus
)
from stores.sqlite_store import SQLiteStore
from utils.time_parser import TimeParser


class RetrievalMode(str, Enum):
    """检索模式"""
    FTS5 = "fts5"
    EMBEDDING = "embedding"
    HYBRID = "hybrid"


class MemoryManager:
    """核心记忆管理器"""

    def __init__(self, config: dict):
        self.config = config
        self.mode = RetrievalMode(config.get("retrieval_mode", "fts5"))

        # 初始化存储
        sqlite_config = config.get("sqlite", {})
        self.store = SQLiteStore(sqlite_config.get("path", "./data/xiaozhi_memory.db"))

        # 初始化检索器
        from core.retriever.fts import FTS5Retriever
        self.retriever = FTS5Retriever(self.store)

        # LLM配置（暂时不实现，预留接口）
        self.llm_config = config.get("llm", {})

    async def add_memory(
        self,
        messages: List[Dict[str, str]],
        user_id: str
    ) -> Dict[str, int]:
        """
        添加记忆

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            user_id: 用户ID

        Returns:
            {"added": 0, "updated": 0, "skipped": 0}
        """
        results = {"added": 0, "updated": 0, "skipped": 0}

        # 提取消息内容
        for msg in messages:
            if msg.get("role") == "system":
                continue

            content = msg.get("content", "")
            if not content:
                continue

            # 解析时间信息
            time_info = TimeParser.parse(content)

            # 判断是否为意图
            is_intention = self._is_intention(content)

            # 创建记忆对象
            if is_intention:
                memory = IntentionMemory(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    content=content,
                    time_info=time_info if time_info['absolute'] else None,
                    planned_time=datetime.fromisoformat(time_info['absolute']) if time_info['absolute'] else None,
                    time_description=time_info['relative'] if time_info['relative'] else None
                )
            else:
                memory = FactMemory(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    content=content,
                    time_info=time_info if time_info['absolute'] else None
                )

            # 检查是否已存在相似记忆
            existing = await self._find_similar(memory.content, user_id)

            if existing:
                # 更新
                await self._update_memory(existing.id, memory)
                results["updated"] += 1
            else:
                # 添加
                self.store.add(memory)
                results["added"] += 1

        return results

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10
    ) -> List[BaseMemory]:
        """
        搜索记忆

        Args:
            query: 查询文本
            user_id: 用户ID
            top_k: 返回结果数量

        Returns:
            记忆列表
        """
        return await self.retriever.retrieve(query, user_id, top_k)

    async def get_upcoming_intentions(
        self,
        user_id: str,
        days: int = 7
    ) -> List[IntentionMemory]:
        """
        获取未来N天的意图/计划

        Args:
            user_id: 用户ID
            days: 天数

        Returns:
            意图记忆列表
        """
        now = datetime.now()
        future = now + timedelta(days=days)

        return self.store.get_intentions_in_range(user_id, now, future)

    async def update_intention_status(
        self,
        memory_id: str,
        status: IntentionStatus
    ) -> bool:
        """
        更新意图状态

        Args:
            memory_id: 记忆ID
            status: 新状态

        Returns:
            是否成功
        """
        update_data = {
            "intention_status": status.value
        }

        if status == IntentionStatus.COMPLETED:
            update_data["completed_at"] = datetime.now()

        return self.store.update(memory_id, update_data)

    async def get_all_memories(self, user_id: str) -> List[BaseMemory]:
        """获取用户所有记忆"""
        return self.store.get_by_user(user_id)

    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        return self.store.delete(memory_id)

    async def _find_similar(
        self,
        content: str,
        user_id: str,
        threshold: float = 0.8
    ) -> Optional[BaseMemory]:
        """
        查找相似记忆

        Args:
            content: 内容
            user_id: 用户ID
            threshold: 相似度阈值

        Returns:
            相似记忆或None
        """
        # 使用FTS5搜索
        results = self.store.search_fts(content, user_id, top_k=5)

        # 检查是否有完全匹配或高度相似的
        for memory, score in results:
            # 简单的字符串相似度检查
            if self._string_similarity(content, memory.content) > threshold:
                return memory

        return None

    def _string_similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度（简单版）"""
        if s1 == s2:
            return 1.0

        # 简单的包含关系
        if s1 in s2 or s2 in s1:
            return 0.9

        # 编辑距离（简化版）
        longer = max(s1, s2, key=len)
        shorter = min(s1, s2, key=len)

        if len(longer) == 0:
            return 1.0

        # 计算共同字符数
        common = sum(1 for c in shorter if c in longer)
        return common / len(longer)

    def _is_intention(self, text: str) -> bool:
        """
        判断是否为意图/计划

        意图关键词:
        - 想、要、打算、计划、准备
        - 明天、后天、下周、下月
        - 约、预约、定、安排
        """
        intention_keywords = [
            r'想(要|去|做|买|预约|定)',
            r'要(去|做|买|预约|定)',
            r'打算|计划|准备',
            r'明天|后天|下周|下月',
            r'预约|定个?|安排',
            r'记得(去|做|买)'
        ]

        for pattern in intention_keywords:
            if re.search(pattern, text):
                return True

        return False

    async def _update_memory(self, memory_id: str, new_memory: BaseMemory):
        """更新记忆"""
        update_data = {
            "content": new_memory.content,
            "updated_at": datetime.now()
        }

        if isinstance(new_memory, IntentionMemory):
            if new_memory.planned_time:
                update_data["planned_time"] = new_memory.planned_time
            if new_memory.time_description:
                update_data["time_description"] = new_memory.time_description
            if new_memory.intention_type:
                update_data["intention_type"] = new_memory.intention_type

        if new_memory.time_info:
            update_data["time_info"] = new_memory.time_info

        self.store.update(memory_id, update_data)

    def close(self):
        """关闭连接"""
        if hasattr(self, 'store'):
            self.store.close()


# 便捷函数
_default_manager: Optional[MemoryManager] = None


def get_manager(config: Optional[dict] = None) -> MemoryManager:
    """获取默认记忆管理器"""
    global _default_manager
    if _default_manager is None:
        if config is None:
            config = {
                "retrieval_mode": "fts5",
                "sqlite": {"path": "./data/xiaozhi_memory.db"}
            }
        _default_manager = MemoryManager(config)
    return _default_manager
