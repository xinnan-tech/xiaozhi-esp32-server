from ..base import MemoryProviderBase, logger
from mem0 import Memory

TAG = __name__

class MemoryProvider(MemoryProviderBase):
    def __init__(self, config):
        super().__init__(config)
        config = {
            "llm": {
                "provider": "deepseek",
                "config": {
                    "model": "qwen-plus", #模型可替换
                    "deepseek_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",　#API-URL 可替换
                    "api_key": "sk-xxxxxxxxxxxx", #填写API-key
                    "temperature": 0.2,
                    "max_tokens": 2000,
                    "top_p": 1.0
                }
            },
            "embedder": {
                "provider": "huggingface",
                "config": {
                    "model": "/mnt/mem0/m3e-large"　#可以替换在线模型或者使用本地模型
                }
            },
            "vector_store": {
                "provider": "milvus",　#可以使用容器本地部署milvus向量数据库
                "config": {
                    "url": "http://localhost:19530",　#使用本地的milvus向量数据库
                    "collection_name": "mem0_collection",
                    "embedding_model_dims": 1024
                }
            }
        }

        self.use_mem0 = False
        self.client = Memory.from_config(config)
        self.use_mem0 = True

    async def save_memory(self, msgs):
        if not self.use_mem0:
            return None
        if len(msgs) < 2:
            return None
        
        try:
            # Format the content as a message list for mem0
            messages = [
                {"role": message.role, "content": message.content}
                for message in msgs if message.role != "system"
            ]
            result = self.client.add(messages, user_id=self.role_id)
            logger.bind(tag=TAG).info(f"Save memory result: {result}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"保存记忆失败: {str(e)}")
            return None

    async def query_memory(self, query: str)-> str:
        if not self.use_mem0:
            return ""
        try:
            results = self.client.search(
                query,
                user_id=self.role_id
            )
            logger.bind(tag=TAG).info(f"get memory result: {results}")
            if not results or 'results' not in results:
                return ""
                
            # Format each memory entry with its update time up to minutes
            memories = []
            for entry in results['results']:
                timestamp = entry.get('updated_at', '') or entry.get('created_at', '')
                if timestamp:
                    try:
                        # Parse and reformat the timestamp
                        dt = timestamp.split('.')[0]  # Remove milliseconds
                        formatted_time = dt.replace('T', ' ')
                    except:
                        formatted_time = timestamp
                memory = entry.get('memory', '')
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
            if "collection not found" in e:
                return ""
            else:
                logger.bind(tag=TAG).error(f"查询记忆失败: {str(e)}")
            return ""
