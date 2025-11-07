import traceback
from typing import Optional

from ..base import MemoryProviderBase, logger
from mem0 import MemoryClient
from core.utils.util import check_model_key

TAG = __name__


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory=None):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.api_version = config.get("api_version", "v1.1")
        model_key_msg = check_model_key("Mem0ai", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
            self.use_mem0 = False
            return
        else:
            self.use_mem0 = True

        try:
            self.client = MemoryClient(api_key=self.api_key)
            logger.bind(tag=TAG).info("成功连接到 Mem0ai 服务")
        except Exception as e:
            logger.bind(tag=TAG).error(f"连接到 Mem0ai 服务时发生错误: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
            self.use_mem0 = False

    async def save_memory(self, msgs):
        if not self.use_mem0:
            return None
        if len(msgs) < 2:
            return None

        try:
            # Format the content as a message list for mem0
            messages = [
                {"role": message.role, "content": message.content}
                for message in msgs
                if message.role != "system"
            ]
            result = self.client.add(
                messages, user_id=self.role_id, output_format=self.api_version
            )
            logger.bind(tag=TAG).debug(f"Save memory result: {result}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"保存记忆失败: {str(e)}")
            return None

    async def query_memory(self, query: str) -> str:
        if not self.use_mem0:
            return ""
        try:
            results = self.client.search(
                query, user_id=self.role_id, output_format=self.api_version
            )
            if not results or "results" not in results:
                return ""

            # Format each memory entry with its update time up to minutes
            memories = []
            for entry in results["results"]:
                timestamp = entry.get("updated_at", "")
                if timestamp:
                    try:
                        # Parse and reformat the timestamp
                        dt = timestamp.split(".")[0]  # Remove milliseconds
                        formatted_time = dt.replace("T", " ")
                    except:
                        formatted_time = timestamp
                memory = entry.get("memory", "")
                if timestamp and memory:
                    # Store tuple of (timestamp, formatted_string) for sorting
                    memories.append((timestamp, f"[{formatted_time}] {memory}"))

            # Sort by timestamp in descending order (newest first)
            memories.sort(key=lambda x: x[0], reverse=True)

            # Extract only the formatted strings
            memories_str = "\n".join(f"- {memory[1]}" for memory in memories)
            logger.bind(tag=TAG).debug(f"Query results: {memories_str}")
            return memories_str
        except Exception as e:
            logger.bind(tag=TAG).error(f"查询记忆失败: {str(e)}")
            return ""

    def get_user_persona(self) -> Optional[str]:
        """获取格式化的用户画像信息（用于 prompt）
        
        Returns:
            格式化后的用户画像字符串，如果无记忆则返回 None
        """
        if not self.use_mem0:
            return None
        
        try:
            # 使用通用查询获取所有记忆
            results = self.client.search(
                "user information, preferences, background, personal details",
                user_id=self.role_id,
                output_format=self.api_version,
                limit=10  # 限制返回数量
            )
            
            if not results or "results" not in results:
                return None
            
            # 格式化记忆条目
            persona_items = []
            for entry in results["results"]:
                memory = entry.get("memory", "")
                if memory:
                    persona_items.append(f"- {memory}")
            
            return "\n".join(persona_items) if persona_items else None
            
        except Exception as e:
            logger.bind(tag=TAG).debug(f"获取用户画像失败: {str(e)}")
            return None
