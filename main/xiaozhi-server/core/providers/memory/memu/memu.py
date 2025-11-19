import traceback

from ..base import MemoryProviderBase, logger
from memu import MemuClient
from core.utils.util import check_model_key

TAG = __name__


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory=None):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.memu.so")
        self.user_name = config.get("user_name", "用户")
        self.agent_name = config.get("agent_name", "小智")

        model_key_msg = check_model_key("MemU", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
            self.use_memu = False
            return
        else:
            self.use_memu = True

        try:
            self.client = MemuClient(
                base_url=self.base_url,
                api_key=self.api_key
            )
            logger.bind(tag=TAG).info("成功连接到 MemU 服务")
        except Exception as e:
            logger.bind(tag=TAG).error(f"连接到 MemU 服务时发生错误: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
            self.use_memu = False

    async def save_memory(self, msgs, context=None):
        if not self.use_memu:
            return None
        if len(msgs) < 2:
            return None

        try:
            # Format the conversation as a single text string for memU
            conversation_text = ""
            for message in msgs:
                if message.role == "system":
                    continue
                role_name = self.user_name if message.role == "user" else self.agent_name
                conversation_text += f"{role_name}: {message.content}\n"

            if not conversation_text.strip():
                return None

            # 准备session_date参数（MEMu SDK支持的参数）
            import time
            from datetime import datetime
            
            session_date = None
            context_info = {}
            if context:
                # 记录上下文信息到日志
                if "session_id" in context:
                    context_info["session_id"] = context["session_id"]
                if "mac_address" in context:
                    context_info["mac_address"] = context["mac_address"]
                if "device_id" in context:
                    context_info["device_id"] = context["device_id"]
                
                # 使用当前时间作为session_date
                session_date = datetime.now().strftime("%Y-%m-%d")
            
            # Use memorize_conversation to store the memory
            result = self.client.memorize_conversation(
                conversation=conversation_text.strip(),
                user_id=self.role_id,
                user_name=self.user_name,
                agent_id="xiaozhi_agent",
                agent_name=self.agent_name,
                session_date=session_date
            )
            logger.bind(tag=TAG).info(f"保存记忆成功，context: {context_info}, session_date: {session_date}")
            logger.bind(tag=TAG).debug(f"Save memory result: {result}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"保存记忆失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
            return None

    async def query_memory(self, query: str) -> str:
        if not self.use_memu:
            return ""
        try:
            # Use retrieve_related_memory_items to retrieve memories
            results = self.client.retrieve_related_memory_items(
                user_id=self.role_id,
                agent_id="xiaozhi_agent",
                query=query,
                top_k=10,
                min_similarity=0.3
            )

            # 转换结果
            if hasattr(results, 'model_dump'):
                data = results.model_dump()
            elif hasattr(results, 'dict'):
                data = results.dict() if callable(results.dict) else results
            else:
                data = results
            
            # 检查是否有记忆项
            memory_items = []
            if isinstance(data, dict) and 'memory_items' in data:
                memory_items = data['memory_items']
            elif isinstance(data, list):
                memory_items = data

            if not memory_items:
                return ""

            # Format each memory entry with its timestamp
            memories = []
            for entry in memory_items:
                if hasattr(entry, 'model_dump'):
                    entry_dict = entry.model_dump()
                elif hasattr(entry, 'dict'):
                    entry_dict = entry.dict() if callable(entry.dict) else entry
                else:
                    entry_dict = entry
                
                timestamp = entry_dict.get("created_at", "")
                if timestamp:
                    try:
                        # Parse and reformat the timestamp
                        dt = timestamp.split(".")[0]  # Remove milliseconds
                        formatted_time = dt.replace("T", " ")
                    except:
                        formatted_time = timestamp
                else:
                    formatted_time = "未知时间"
                    
                memory = entry_dict.get("content", "") or entry_dict.get("memory", "")
                if memory:
                    # Store tuple of (timestamp, formatted_string) for sorting
                    memories.append((timestamp, f"[{formatted_time}] {memory}"))

            if not memories:
                return ""

            # Sort by timestamp in descending order (newest first)
            memories.sort(key=lambda x: x[0], reverse=True)

            # Extract only the formatted strings
            memories_str = "\n".join(f"- {memory[1]}" for memory in memories)
            logger.bind(tag=TAG).debug(f"Query results: {memories_str}")
            return memories_str
        except Exception as e:
            logger.bind(tag=TAG).error(f"查询记忆失败: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
            return ""
