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

        # LLM 客户端
        self.llm_client = self._init_llm_client(config.get("llm", {}))
        self.extraction_config = config.get("extraction", {
            "enabled": False,
            "max_retrieved_memories": 20,
            "max_recent_memories": 10,
            "observation_date_delta": 0
        })

        # 会话级别的最近提取记忆（用于去重）
        self._session_extracted: List[str] = []

    def _init_llm_client(self, llm_config: dict):
        """初始化 LLM 客户端"""
        if not llm_config.get("provider"):
            return None

        provider = llm_config["provider"]

        if provider == "openai":
            from llm.openai_client import OpenAIClient
            return OpenAIClient(
                api_key=llm_config["api_key"],
                model=llm_config.get("model", "gpt-4o-mini"),
                base_url=llm_config.get("base_url")
            )

        return None

    async def add_memory(
        self,
        messages: List[Dict[str, str]],
        device_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        添加记忆

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            device_id: 设备ID
            user_id: 用户ID（可选）

        Returns:
            {"added": 0, "updated": 0, "skipped": 0}
        """
        # 格式化消息
        formatted_messages = self._format_messages(messages)
        if not formatted_messages:
            return {"added": 0, "updated": 0, "skipped": 0}

        # 判断是否使用 LLM 提取
        if self.llm_client and self.extraction_config.get("enabled", False):
            return await self._add_memory_with_llm(formatted_messages, device_id, user_id)
        else:
            return await self._add_memory_with_rules(formatted_messages, device_id, user_id)

    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """格式化消息，过滤系统消息和空内容"""
        formatted = []
        for msg in messages:
            if msg.get("role") == "system":
                continue

            content = msg.get("content", "")
            if not content:
                continue

            # 处理 JSON 格式（ASR 情感标签等）
            if content.startswith("{") and content.endswith("}"):
                import json
                try:
                    data = json.loads(content)
                    if "text" in data:
                        content = data["text"]
                except json.JSONDecodeError:
                    pass

            formatted.append({"role": msg.get("role", "user"), "content": content})

        return formatted

    async def _add_memory_with_llm(
        self,
        messages: List[Dict[str, str]],
        device_id: str,
        user_id: Optional[str]
    ) -> Dict[str, int]:
        """使用 LLM 提取记忆"""
        results = {"added": 0, "updated": 0, "skipped": 0}

        # 1. 获取上下文
        context = await self._build_extraction_context(device_id, user_id, messages)

        # 2. 构建对话文本
        conversation = self._build_conversation_text(messages)

        # 3. LLM 提取
        try:
            facts = await self.llm_client.extract_facts(conversation, context)
        except Exception as e:
            # LLM 失败时回退到规则提取
            import logging
            logging.error(f"[xiaozhi-memory] LLM extraction failed, falling back to rule-based: {e}")
            return await self._add_memory_with_rules(messages, device_id, user_id)

        # 4. 处理提取的事实
        for fact in facts:
            # 去重检查
            existing = await self._find_duplicate(fact.get("content", ""), device_id, user_id)

            if existing:
                results["updated"] += 1
            else:
                # 创建记忆对象
                memory = self._fact_to_memory(fact, device_id, user_id)
                self.store.add(memory)

                # 记录到会话提取列表
                self._session_extracted.append(fact.get("content", ""))

                results["added"] += 1

        return results

    async def _add_memory_with_rules(
        self,
        messages: List[Dict[str, str]],
        device_id: str,
        user_id: Optional[str]
    ) -> Dict[str, int]:
        """使用规则匹配提取记忆（原有逻辑）"""
        results = {"added": 0, "updated": 0, "skipped": 0}

        for msg in messages:
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
                    device_id=device_id,
                    user_id=user_id,
                    content=content,
                    time_info=time_info if time_info['absolute'] else None,
                    planned_time=datetime.fromisoformat(time_info['absolute']) if time_info['absolute'] else None,
                    time_description=time_info['relative'] if time_info['relative'] else None
                )
            else:
                memory = FactMemory(
                    id=str(uuid.uuid4()),
                    device_id=device_id,
                    user_id=user_id,
                    content=content,
                    time_info=time_info if time_info['absolute'] else None
                )

            # 检查是否已存在相似记忆
            existing = await self._find_similar(memory.content, device_id, user_id)

            if existing:
                await self._update_memory(existing.id, memory)
                results["updated"] += 1
            else:
                self.store.add(memory)
                results["added"] += 1

        return results

    async def _build_extraction_context(
        self,
        device_id: str,
        user_id: Optional[str],
        messages: List[Dict]
    ) -> dict:
        """构建 LLM 提取的上下文"""
        config = self.extraction_config
        current_date = datetime.now()
        observation_date = current_date + timedelta(days=config.get("observation_date_delta", 0))

        # 获取最近提取的记忆（用于去重）
        recently_extracted = self._session_extracted[:config.get("max_recent_memories", 10)]

        # 获取相关现有记忆（用于链接）
        query_text = " ".join([m.get("content", "") for m in messages[-3:]])
        existing_memories = self.store.search_fts(query_text, device_id, user_id, top_k=config.get("max_retrieved_memories", 20))
        existing_formatted = [
            {"id": m[0].id, "text": m[0].content}
            for m in existing_memories
        ]

        return {
            "current_date": current_date.strftime("%Y-%m-%d"),
            "observation_date": observation_date.strftime("%Y-%m-%d"),
            "recently_extracted": "\n".join(f"- {r}" for r in recently_extracted) if recently_extracted else "无",
            "existing_memories": "\n".join(f"[{e['id']}] {e['text']}" for e in existing_formatted) if existing_formatted else "无"
        }

    def _build_conversation_text(self, messages: List[Dict]) -> str:
        """构建对话文本"""
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            role_name = "User" if role == "user" else "Assistant"
            lines.append(f"{role_name}: {content}")
        return "\n".join(lines)

    async def _find_duplicate(
        self,
        content: str,
        device_id: str,
        user_id: Optional[str],
        threshold: float = 0.85
    ) -> Optional[BaseMemory]:
        """查找重复记忆"""
        results = self.store.search_fts(content, device_id, user_id, top_k=5)

        for memory, score in results:
            if self._string_similarity(content, memory.content) > threshold:
                return memory

        return None

    def _fact_to_memory(self, fact: dict, device_id: str, user_id: Optional[str]) -> BaseMemory:
        """将 LLM 提取的事实转换为记忆对象"""
        fact_type = fact.get("type", "FACT")

        common_data = {
            "id": str(uuid.uuid4()),
            "device_id": device_id,
            "user_id": user_id,
            "content": fact["content"],
            "time_info": fact.get("time_info"),
            "related_ids": fact.get("linked_memory_ids", []),
        }

        if fact_type == "INTENTION":
            common_data.update({
                "intention_status": IntentionStatus.PLANNED,
                "intention_type": fact.get("intention_type"),
            })

            # 解析时间
            time_info = fact.get("time_info", {})
            if time_info and time_info.get("absolute"):
                try:
                    common_data["planned_time"] = datetime.fromisoformat(time_info["absolute"])
                except ValueError:
                    pass

            if time_info and time_info.get("relative"):
                common_data["time_description"] = time_info["relative"]

            return IntentionMemory(**common_data)

        elif fact_type == "PREFERENCE":
            return PreferenceMemory(**common_data)

        return FactMemory(**common_data)

    async def search(
        self,
        query: str,
        device_id: str,
        user_id: Optional[str] = None,
        top_k: int = 10
    ) -> List[BaseMemory]:
        """
        搜索记忆

        Args:
            query: 查询文本
            device_id: 设备ID
            user_id: 用户ID（可选）
            top_k: 返回结果数量

        Returns:
            记忆列表
        """
        return await self.retriever.retrieve(query, device_id, user_id, top_k)

    async def get_upcoming_intentions(
        self,
        device_id: str,
        user_id: Optional[str] = None,
        days: int = 7
    ) -> List[IntentionMemory]:
        """
        获取未来N天的意图/计划

        Args:
            device_id: 设备ID
            user_id: 用户ID（可选）
            days: 天数

        Returns:
            意图记忆列表
        """
        now = datetime.now()
        future = now + timedelta(days=days)

        return self.store.get_intentions_in_range(device_id, user_id, now, future)

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

    async def get_all_memories(self, device_id: str, user_id: Optional[str] = None) -> List[BaseMemory]:
        """获取设备/用户所有记忆"""
        return self.store.get_by_device(device_id, user_id)

    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        return self.store.delete(memory_id)

    async def _find_similar(
        self,
        content: str,
        device_id: str,
        user_id: Optional[str],
        threshold: float = 0.8
    ) -> Optional[BaseMemory]:
        """
        查找相似记忆

        Args:
            content: 内容
            device_id: 设备ID
            user_id: 用户ID（可选）
            threshold: 相似度阈值

        Returns:
            相似记忆或None
        """
        # 使用FTS5搜索
        results = self.store.search_fts(content, device_id, user_id, top_k=5)

        # 检查是否有完全匹配或高度相似的
        for memory, score in results:
            # 简单的字符串相似度检查
            if self._string_similarity(content, memory.content) > threshold:
                return memory

        return None

    def _string_similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度（基于字符重合度）"""
        if s1 == s2:
            return 1.0

        # 简单的包含关系
        if s1 in s2 or s2 in s1:
            return 0.9

        if len(s1) == 0 or len(s2) == 0:
            return 0.0

        # 注意：等长时 max/min(key=len) 会返回同一个字符串，导致 common 恒等于
        # len(longer)、相似度恒为 1.0 的 bug（任意等长字符串被判为完全相同）。
        # 这里显式区分 longer/shorter。
        if len(s1) >= len(s2):
            longer, shorter = s1, s2
        else:
            longer, shorter = s2, s1

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
        from utils.tokenizer import tokenize_to_string
        update_data = {
            "content": new_memory.content,
            # 同步更新 tokens，否则 FTS5 触发器会用新 content + 旧 tokens 重建索引，
            # 导致 content 与 tokens 错位、检索失效。
            "tokens": tokenize_to_string(new_memory.content),
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

    async def get_user_profile(self, device_id: str) -> Optional[BaseMemory]:
        """
        获取设备用户画像

        Args:
            device_id: 设备ID

        Returns:
            用户画像或None
        """
        memories = self.store.get_by_device(device_id, user_id=None)
        for m in memories:
            if m.type.value == "profile":
                return m
        return None

    async def create_or_update_profile(self, device_id: str, profile_data: dict) -> BaseMemory:
        """
        创建或更新用户画像

        Args:
            device_id: 设备ID
            profile_data: 画像数据

        Returns:
            用户画像
        """
        from memories.base import UserProfile

        existing = await self.get_user_profile(device_id)

        if existing:
            # 更新现有画像
            update_data = {
                **profile_data,
                "updated_at": datetime.now()
            }
            self.store.update(existing.id, update_data)
            # 返回更新后的画像
            memories = self.store.get_by_device(device_id, user_id=None)
            for m in memories:
                if m.type.value == "profile":
                    return m
        else:
            # 创建新画像
            profile = UserProfile(
                id=str(uuid.uuid4()),
                device_id=device_id,
                user_id=None,
                **profile_data
            )
            self.store.add(profile)
            return profile

    async def record_first_meeting(self, device_id: str):
        """
        记录或更新第一次见面时间

        Args:
            device_id: 设备ID

        Returns:
            互动天数
        """
        from memories.base import UserProfile
        now = datetime.now()

        existing = await self.get_user_profile(device_id)

        if existing is None:
            # 首次见面，创建用户画像
            profile = {
                "first_met": now,
                "last_interaction": now,
                "total_interaction_days": 1
            }
            await self.create_or_update_profile(device_id, profile)
            return 1
        else:
            # 更新互动天数
            days = 1
            if existing.first_met:
                # 计算从第一次见面到现在的天数
                delta = now - existing.first_met
                days = delta.days + 1

            # 更新画像
            await self.create_or_update_profile(device_id, {
                "last_interaction": now,
                "total_interaction_days": days
            })
            return days

    async def get_interaction_days(self, device_id: str) -> int:
        """
        获取互动天数

        Args:
            device_id: 设备ID

        Returns:
            互动天数
        """
        profile = await self.get_user_profile(device_id)
        if profile:
            return profile.total_interaction_days or 1
        return 1

    async def get_days_since_last_interaction(self, device_id: str) -> Optional[int]:
        """
        获取距离上次互动的天数

        Args:
            device_id: 设备ID

        Returns:
            距上次互动的天数，如果没有记录返回None
        """
        profile = await self.get_user_profile(device_id)
        if profile and profile.last_interaction:
            delta = datetime.now() - profile.last_interaction
            return delta.days
        return None


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
