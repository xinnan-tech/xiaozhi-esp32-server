import json
import sys
import os
import asyncio
from datetime import datetime

from ..base import MemoryProviderBase, logger

TAG = __name__

# 添加 xiaozhi-memory 路径
XIAOZHI_MEMORY_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../xiaozhi-memory"))
if os.path.exists(XIAOZHI_MEMORY_PATH):
    sys.path.insert(0, XIAOZHI_MEMORY_PATH)


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory=None):
        super().__init__(config)
        self.db_path = config.get("db_path", "./data/xiaozhi_memory.db")
        self.manager = None

        try:
            from core import MemoryManager
            cfg = {
                "retrieval_mode": config.get("retrieval_mode", "fts5"),
                "sqlite": {"path": self.db_path},
                # TODO: 临时写死 LLM 配置用于测试
                "llm": {
                    "provider": "openai",
                    "api_key": "6202d63d-377b-4bd7-a2ad-c162ed977c24",
                    "model": "doubao-seed-2-0-lite-260428",
                    "base_url": "https://ark.cn-beijing.volces.com/api/v3"
                },
                "extraction": {
                    "enabled": True,
                    "max_retrieved_memories": 20,
                    "max_recent_memories": 10,
                    "observation_date_delta": 0
                }
            }
            self.manager = MemoryManager(cfg)
            logger.bind(tag=TAG).info(f"成功初始化 aipet 记忆服务: {self.db_path}")
            logger.bind(tag=TAG).info(f"LLM 提取已启用: {cfg['llm']['model']}")
        except ImportError as e:
            logger.bind(tag=TAG).error(f"xiaozhi-memory 未安装: {e}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"初始化 aipet 记忆服务失败: {e}")

    async def save_memory(self, msgs, session_id=None):
        """保存记忆"""
        if not self.manager or not self.role_id:
            return

        try:
            # 格式化消息
            messages = []
            for msg in msgs:
                if msg.role in ("system", "tool"):
                    continue

                content = msg.content
                if not content:
                    continue

                # 处理 JSON 格式（ASR 情感标签）
                try:
                    if content.strip().startswith("{"):
                        data = json.loads(content)
                        if "content" in data:
                            content = data["content"]
                except (json.JSONDecodeError, KeyError):
                    pass

                messages.append({"role": msg.role, "content": content})

            if messages:
                result = await self.manager.add_memory(messages, self.role_id)
                logger.bind(tag=TAG).debug(f"保存记忆结果: {result}")

        except Exception as e:
            logger.bind(tag=TAG).error(f"保存记忆失败: {e}")

        return None

    async def query_memory(self, query: str) -> str:
        """查询记忆"""
        if not self.manager or not self.role_id:
            return ""

        try:
            search_query = query
            # 处理 JSON 格式
            try:
                if query.strip().startswith("{"):
                    data = json.loads(query)
                    if "content" in data:
                        search_query = data["content"]
            except (json.JSONDecodeError, KeyError):
                pass

            results = await self.manager.search(search_query, self.role_id, top_k=30)

            if not results:
                return ""

            # 格式化记忆
            memories = []
            for m in results:
                timestamp = m.created_at.strftime("%Y-%m-%d %H:%M") if m.created_at else ""
                content = m.content
                if timestamp and content:
                    memories.append((timestamp, f"[{timestamp}] {content}"))

            # 按时间排序
            memories.sort(key=lambda x: x[0], reverse=True)
            return "\n".join(f"- {m[1]}" for m in memories)

        except Exception as e:
            logger.bind(tag=TAG).error(f"查询记忆失败: {e}")
            return ""

    def close(self):
        """关闭连接"""
        if self.manager:
            self.manager.close()
