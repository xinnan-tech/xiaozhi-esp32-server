import traceback
from pyobvector import MilvusLikeClient
from ..base import MemoryProviderBase, logger


TAG = __name__

class MemoryProvider(MemoryProviderBase):
    def __init__(self, config):
        super().__init__(config)
        self.uri = config.get("uri", "")
        self.user = config.get("user", "root@xiaozhi")
        self.password = config.get("password", "root")
        self.db_name = config.get("database", "xiaozhi")
        self.table_name = config.get("table_name", "xiaozhi")
        logger.bind(tag=TAG).info(f"连接到 oceanbase 服务: {self.uri}")
        self.client = self.connect_to_client()

    def connect_to_client(self):
        try:
            return MilvusLikeClient(uri=self.uri, user=self.user,password=self.password, db_name=self.db_name)
        except Exception as e:
            logger.bind(tag=TAG).error(f"连接到 oceanbase 服务时发生错误: {str(e)}")
            logger.bind(tag=TAG).error(f"详细错误: {traceback.format_exc()}")
            return None

    def init_memory(self, role_id, llm):
        super().init_memory(role_id, llm)

    async def save_memory(self, msgs):
        if not self.client or len(msgs) < 2:
            return None

        try:
            messages = [{"role": message.role, "content": message.content} for message in msgs if message.role != "system"]
            for i in range(0, len(messages), 1):
                self.client.insert(collection_name=self.table_name, data=messages[i:i+1])
            logger.bind(tag=TAG).debug("Save memory")
        except Exception as e:
            logger.bind(tag=TAG).error(f"保存记忆失败: {str(e)}")
            return None

    async def query_memory(self, query: str) -> str:
        if not self.client:
            return ""

        try:
            results = self.client.search(
                collection_name=self.table_name,
                data=[query],
                anns_field="embedding",
                limit=5,
                output_fields=["id", "metadata"],
            )
            memories = self.format_memories(results)
            return "\n".join(f"- {memory[1]}" for memory in memories)
        except Exception as e:
            logger.bind(tag=TAG).error(f"查询记忆失败: {str(e)}")
            return ""

    def format_memories(self, results):
        memories = []
        for entry in results['results']:
            timestamp = entry.get('updated_at', '')
            if timestamp:
                try:
                    dt = timestamp.split('.')[0]
                    formatted_time = dt.replace('T', ' ')
                except:
                    formatted_time = timestamp
            memory = entry.get('memory', '')
            if timestamp and memory:
                memories.append((timestamp, f"[{formatted_time}] {memory}"))
        memories.sort(key=lambda x: x[0], reverse=True)
        return memories