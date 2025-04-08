import os.path
import traceback
from pyobvector import MilvusLikeClient
from sentence_transformers import SentenceTransformer

from core.providers.memory.base import MemoryProviderBase

TAG = __name__

create_table_sql = """
CREATE TABLE xiaozhi(
    id INT AUTO_INCREMENT PRIMARY KEY, 
    role VARCHAR(200),
    content text,
    embedding VECTOR(384),
    VECTOR INDEX idx1(embedding) WITH (distance=L2, type=hnsw)
    );
"""


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config):
        super().__init__(config)
        self.uri = config.get("uri", "localhost")
        self.user = config.get("user", "root@test")
        self.password = config.get("password", "")
        self.db_name = config.get("database", "xiaozhi")
        self.table_name = config.get("table_name", "xiaozhi")
        self.model_path = config.get("model_path", "models/all-MiniLM-L6-v2")
        self.model_path = os.path.abspath(self.model_path)
        if not os.path.exists(self.model_path):
            raise Exception(f"模型路径不存在,请下载到: {self.model_path}")
        print(f"连接到 oceanbase 服务: {self.uri}")
        self.client = self.connect_to_client()

    def connect_to_client(self):
        try:
            return MilvusLikeClient(uri=self.uri, user=self.user,password=self.password, db_name=self.db_name)
        except Exception as e:
            print(f"连接到 oceanbase 服务时发生错误: {str(e)}")
            print(f"请检查配置并确认表是否存在: 初始化sql: {create_table_sql}")
            print(f"详细错误: {traceback.format_exc()}")
            return None

    def _string_to_embeddings(self, sentences):
        # 加载预训练的 'all-MiniLM-L6-v2' 模型
        model = SentenceTransformer(self.model_path )
        embeddings = model.encode(sentences)
        return embeddings

    def init_memory(self, role_id, llm):
        super().init_memory(role_id, llm)
        pass

    async def save_memory(self, msgs):
        if not self.client or len(msgs) < 2:
            return None

        try:

            messages =[]
            for message in msgs:
                if message.role != "system":
                    if message.content:
                        messages.append({"role": message.role, "content": message.content,
                                        "embedding": self._string_to_embeddings(message.content)})

            for i in range(0, len(messages), 1):
                self.client.insert(collection_name=self.table_name, data=messages[i:i+1])
            print(f"Save memory")
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            print(f"保存记忆失败: {str(e)}")
            return None

    async def query_memory(self, query: str) -> str:
        if not self.client:
            return ""

        # 把 query 向量化
        query = self._string_to_embeddings(query)

        try:
            results = self.client.search(
                collection_name=self.table_name,
                data=query,
                anns_field="embedding",
                limit=5,
                output_fields=["role", "content"]
            )
            return results
            memories = self.format_memories(results)
            return "\n".join(f"- {memory[1]}" for memory in memories)
        except Exception as e:
            print(f"查询记忆失败: {str(e)}")
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