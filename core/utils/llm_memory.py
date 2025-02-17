import hashlib
import threading
import json
import os
from collections import deque
import uuid

from numpy.linalg import norm
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
# Cosine similarity function
cos_sim = lambda a, b: (a @ b.T) / (norm(a) * norm(b))


import numpy as np

class IntentRecognizer:
    intent_embeddings_cache = {}
    cache_lock = threading.Lock()
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        # 存储注册的意图和相似度阈值以及对应的回调函数
        self.intent_callbacks = []
        
    def register_intent(self, intent_phrases, callback_function, similarity_threshold=0.7):
        """
        注册一个意图
        :param intent_phrases: 意图相关的短语列表
        :param callback_function: 对应的回调函数
        :param similarity_threshold: 意图与查询的相似度阈值，默认为0.7
        """
        with self.cache_lock:
            for phrase in intent_phrases:
                # 如果该短语的嵌入已经缓存，则直接使用缓存
                if phrase not in IntentRecognizer.intent_embeddings_cache:
                    # 计算嵌入并缓存
                    intent_embedding = self.embedding_model.encode([phrase])[0]
                    IntentRecognizer.intent_embeddings_cache[phrase] = intent_embedding
                else:
                    # 使用缓存的嵌入
                    intent_embedding = IntentRecognizer.intent_embeddings_cache[phrase]

                # 存储每个意图短语及其对应的回调函数和相似度阈值
                self.intent_callbacks.append({
                    "phrase": phrase,
                    "embedding": intent_embedding,
                    "callback": callback_function,
                    "threshold": similarity_threshold
                })

    def handle_query(self, query: str, *args, **kwargs):
        """
        处理用户查询并进行意图识别，调用匹配的回调函数
        :param query: 用户查询
        :param args: 任意位置参数传递给回调函数
        :param kwargs: 任意关键字参数传递给回调函数
        :return: 回调函数的返回值
        """
        query = query.strip()
        # 计算用户查询的嵌入表示
        query_embedding = self.embedding_model.encode([query])[0]
        
        best_match = None
        highest_similarity = -1
        matched_callback = None

        # 比较查询与注册的意图短语的相似度
        for intent in self.intent_callbacks:
            similarity = np.dot(query_embedding, intent["embedding"]) / (np.linalg.norm(query_embedding) * np.linalg.norm(intent["embedding"]))
            if similarity > highest_similarity and similarity >= intent["threshold"]:
                highest_similarity = similarity
                best_match = intent["phrase"]
                matched_callback = intent["callback"]

        if best_match and matched_callback:
            # 调用与匹配意图对应的回调函数，传递位置参数和关键字参数
            logger.info(f"{query}\t意图识别结果：{best_match}\tfunc:{matched_callback}\t (相似度: {highest_similarity:.2f})")
            return matched_callback(query,*args, **kwargs)
        logger.info(f"{query}\t未识别到意图")
        return None






class MemoryManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MemoryManager, cls).__new__(cls)  
        return cls._instance

    def __init__(
            self,
            llm,
            embd,
            summary_prompt: str = "请总结下面的聊天内容,必须在{content_len}字数以内，必须包含聊天的完整细节:\n\n{content}",
            max_memory_length: int = 1000,
            summary_length: int = 1000,
            max_summary_length: int = 2000,

            memory_dir='memory_data'
        ):
        """
        初始化记忆管理类
        :param embedding_model: 用于生成文本嵌入的模型
        :param max_memory_length: 最大记忆总字符长度
        :param summary_length: 每次生成的总结的长度
        :param memory_file: 保存记忆数据的文件路径
        """
        logger.info(f"初始化记忆管理器 max_memory_length:{max_memory_length} summary_length:{summary_length} max_summary_length:{max_summary_length}")
        self.max_memory_length = max_memory_length
        self.summary_length = summary_length
        self.max_summary_length = max_summary_length

        self.memory_data = {}  # 用字典管理每个用户的记忆
        self.lock = threading.Lock()  # 锁对象，用于线程同步
        self.summary_prompt = summary_prompt
        self.llm = llm
        self.embedding_model = embd  # 用于生成文本的嵌入

        self.memory_dir = memory_dir
        if not os.path.exists(self.memory_dir):
            os.makedirs(self.memory_dir,exist_ok=True)  # 创建目录
        
        # 确保目录具有读写权限
        if not os.access(self.memory_dir, os.W_OK):
            try:
                os.chmod(self.memory_dir, 0o700)  # 设置读写权限
                logger.info(f"已为目录 {self.memory_dir} 设置读写权限")
            except Exception as e:
                logger.warning(f"无法修改 {self.memory_dir} 的权限: {e}")
                raise PermissionError(f"没有足够权限访问目录: {self.memory_dir}")
        # 加载已有记忆或初始化新的记忆
        self.load_memory()
        
        # ThreadPoolExecutor for async tasks
        self.executor = ThreadPoolExecutor()


        self.intent_recognizer = IntentRecognizer(self.embedding_model)
        self.intent_recognizer.register_intent(
            ["回忆对话", "回忆上次讲的", "请回忆","有什么记忆","刚才讲了什么","上次讲了什么"], 
            self._recall_last_conversation, 
            similarity_threshold=0.7
        )
        self.intent_recognizer.register_intent(
            ["删除我的记忆","删除所有记忆"], 
            self._del_all, 
            similarity_threshold=0.9
        )       
    
    def _recall_last_conversation(self,query: str, token_name: str)->str:
        """
        回忆上次的对话
        :param token_name: 用户唯一标识符
        :param query: 用户查询
        :return: 上次的对话内容
        """
        user_memory = self.search_memory(token_name, query, top_k=5)
        

        if len(user_memory) == 0:
            
            user_memory = self.memory_data.get(token_name, {'memory':[]})
            
            user_memory = list(user_memory['memory'])
            user_memory = user_memory[-10:]        

            

        output = "\n".join([msg['content'] for msg in user_memory])

        
        return f"{query}\n\n我们上次聊到了:\n\n{output}"

    def _generate_summary(self, chat_paragraph: list):
        """
        生成聊天内容的总结（可以根据具体要求定制总结逻辑）
        :param chat_content: 聊天内容
        :return: 总结的字符串
        """
        if self.llm is None:
            return "".join([msg['content'] for msg in chat_paragraph])[:self.summary_length]
        
        response_message = []
        try:            
            llm_responses = self.llm.response(
                str(uuid.uuid4()), 
                [
                    {
                        "role": "user", 
                        "content": self.summary_prompt.format(content=json.dumps(chat_paragraph),content_len=self.summary_length)
                    }
                ]
            )
        except Exception as e:
            logger.warning(f"LLM 处理出错 {query}: {e}")
            return None

        for content in llm_responses:
            response_message.append(content)
        return "".join(response_message)

    def _forget_old_memory(self, token_name: str):
        """
        超过最大记忆总长度时，删除不重要的记忆
        :param token_name: 用户唯一标识符
        """
        user_memory = self.memory_data.get(token_name, {'memory': deque(), 'total_length': 0})

        while user_memory['total_length'] > self.max_memory_length and user_memory['memory']:
            # 删除最旧的聊天内容和对应的嵌入
            oldest_message = user_memory['memory'].popleft()
            oldest_embedding = user_memory['embeddings'].popleft()  # Remove corresponding embedding
            user_memory['total_length'] -= len(oldest_message['content'])



    def _update_summary(self, token_name: str, chat_paragraph: list[dict]):
        """
        更新记忆总结，合并每个聊天段落的内容并生成摘要
        :param token_name: 用户唯一标识符
        """      
        
        if len(chat_paragraph) == 0:
            return 
        
        summary = self._generate_summary(chat_paragraph)

        if summary is None or len(summary.strip()) == 0:
            return
        
        self.memory_data[token_name].setdefault('memory_summary', []).append(summary)

        # 生成并保存摘要的嵌入
        summary_embedding = self.embedding_model.encode([summary])[0]
        self.memory_data[token_name].setdefault('summary_embeddings', []).append(summary_embedding)

    def _combine_summary(self, token_name: str):
        """
        将所有的记忆总结合并为一个
        :param token_name: 用户唯一标识符
        """
        
        user_memory = self.memory_data.get(token_name, {'memory_summary': []})

        # 如果没有超过最大总结长度，直接返回
        old_summary = "".join(user_memory['memory_summary'])
        if len(user_memory) == 0 or len(old_summary) < self.max_memory_length:
            logger.debug("不需要合并,总结长度：", len(old_summary))
            return
        logger.debug("合并前的总结长度：", len(old_summary))
        summary = self._generate_summary(user_memory['memory_summary'])
        logger.debug("合并后的总结长度：", len(summary))
        self.memory_data[token_name]['memory_summary'] = [summary]

        # 生成并保存摘要的嵌入
        summary_embedding = self.embedding_model.encode([summary])[0]
        self.memory_data[token_name]['summary_embeddings'] = [summary_embedding]

    def _del_all(self, query:str, token_name: str)->str:
        """
        删除所有记忆
        :param token_name: 用户唯一标识符
        """
        self.memory_data[token_name] = {'memory': deque(), 'total_length': 0, 'memory_summary': [], 'summary_embeddings': [], 'embeddings': deque()}
        self.save_memory()
        return f"你必须{query}\n\n你必须回答同意删除所有记忆"

    async def add_chat_paragraph(self, token_name: str, chat_paragraph: list[dict]):
        """
        添加一段聊天内容到记忆中
        :param token_name: 用户唯一标识符
        :param chat_paragraph: 聊天段落，包含多条聊天记录
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self.executor, self._add_chat_paragraph, token_name, chat_paragraph)

    def _add_chat_paragraph(self, token_name: str, chat_paragraph: list[dict]):
        with self.lock:  # 使用锁保证线程安全
            if token_name not in self.memory_data:
                self.memory_data[token_name] = {'memory': deque(), 'total_length': 0, 'memory_summary': [], 'summary_embeddings': [], 'embeddings': deque()}

            user_memory = self.memory_data[token_name]
            new_embeddings = []

            for message in chat_paragraph:
                role = message['role']
                content = message['content']

                chat_hash = hashlib.md5(content.encode()).hexdigest()

                user_memory['memory'].append({"role": role, "content": content, "hash": chat_hash, "datatime": "{:%Y-%m-%d %H:%M:%S}".format(datetime.now())})
                user_memory['total_length'] += len(content)

                # 生成嵌入
                embedding = self.embedding_model.encode([content])[0]  # 使用嵌入模型生成嵌入
                user_memory['embeddings'].append(embedding)

            # 更新记忆总结
            self._update_summary(token_name, chat_paragraph)

            # 如果记忆超出了限制，删除不重要的内容
            self._forget_old_memory(token_name)

            # 合并压缩记忆总结
            self._combine_summary(token_name)

            # 保存记忆到文件
            self.save_memory()

    def handle_user_scene(self,token_name:str, query: str) -> str:
        """
        解析用户查询
        :param query: 用户查询
        :return: 解析后的查询
        """
        query = query.strip()
        if len(query) == 0:
            return query
        
        result = self.intent_recognizer.handle_query(query, token_name)
        if result is None:
            return query

        return result
    

    def get_memory_summary(self, token_name: str) -> str:
        """
        获取当前用户的记忆总结
        :param token_name: 用户唯一标识符
        :return: 当前的总结
        """
        user_memory = self.memory_data.get(token_name, {'memory_summary': []})
        return "\n\n".join(user_memory['memory_summary'])

    def get_full_memory(self, token_name: str) -> list[str]:
        """
        获取当前用户的完整记忆内容
        :param token_name: 用户唯一标识符
        :return: 当前的所有记忆内容
        """
        user_memory = self.memory_data.get(token_name, {'memory': []})
        return [msg['content'] for msg in user_memory['memory']]

    def search_memory(self, token_name: str, query: str, top_k: int = 5, threshold: float = 0.5):
        """
        使用嵌入进行记忆查询
        :param token_name: 用户唯一标识符
        :param query: 查询内容
        :param top_k: 返回最相似的记忆条数
        :param threshold: 相似度阈值，低于此阈值的结果将被忽略
        :return: 最相似的记忆条目
        """
        user_memory = self.memory_data.get(token_name, {'embeddings': []})
        if not user_memory['embeddings']:
            return []

        # 生成查询的嵌入
        query_embedding = self.embedding_model.encode([query])[0]

        # 计算查询与记忆中每条消息的相似度
        similarities = [cos_sim(query_embedding, embedding) for embedding in user_memory['embeddings']]

        # 获取最相似的记忆条目，过滤相似度低于阈值的结果
        filtered_indices = [i for i, sim in enumerate(similarities) if sim >= threshold]
        top_indices = sorted(filtered_indices, key=lambda i: similarities[i], reverse=True)[:top_k]
        similar_memory = [user_memory['memory'][i] for i in top_indices]

        return similar_memory

    def search_memory_summary(self, token_name: str, query: str, top_k: int = 5, threshold: float = 0.5):
        """
        使用嵌入进行记忆总结查询
        :param token_name: 用户唯一标识符
        :param query: 查询内容
        :param top_k: 返回最相似的记忆条数
        :param threshold: 相似度阈值，低于此阈值的结果将被忽略
        :return: 最相似的记忆总结条目
        """
        user_memory = self.memory_data.get(token_name, {'memory_summary': [], 'summary_embeddings': []})
        if not user_memory['summary_embeddings']:
            return []

        # 生成查询的嵌入
        query_embedding = self.embedding_model.encode([query])[0]

        # 计算查询与记忆总结的相似度
        similarities = [cos_sim(query_embedding, embedding) for embedding in user_memory['summary_embeddings']]

        # 获取最相似的记忆总结条目，过滤相似度低于阈值的结果
        filtered_indices = [i for i, sim in enumerate(similarities) if sim >= threshold]
        top_indices = sorted(filtered_indices, key=lambda i: similarities[i], reverse=True)[:top_k]
        similar_summary = [user_memory['memory_summary'][i] for i in top_indices]

        return similar_summary
    def save_memory(self):
        """
        将记忆保存到本地文件，每个文件以token_name作为文件名
        """
        try:
            for token_name, user_data in self.memory_data.items():
                memory_data_serializable = {
                    'memory': list(user_data['memory']),
                    'total_length': user_data['total_length'],
                    'memory_summary': user_data['memory_summary'],
                    'summary_embeddings': [embedding.tolist() for embedding in user_data['summary_embeddings']],
                    'embeddings': [embedding.tolist() for embedding in user_data['embeddings']]
                }

                file_path = os.path.join(self.memory_dir, f"{token_name}.json")
                with open(file_path, 'w', encoding='utf-8') as file:
                    json.dump(memory_data_serializable, file, ensure_ascii=False, indent=4)
                logger.info(f"记忆已保存至 {file_path}")

        except Exception as e:
            logger.warning(f"保存记忆时出错: {e}")

    def load_memory(self):
        """
        从本地文件加载记忆数据
        """
        try:
            self.memory_data = {}

            for file_name in os.listdir(self.memory_dir):
                if file_name.endswith('.json'):
                    token_name = file_name[:-5]  # 去掉 .json 后缀
                    file_path = os.path.join(self.memory_dir, file_name)

                    with open(file_path, 'r', encoding='utf-8') as file:
                        try:
                            memory_data = json.load(file)
                        except Exception as e:
                            logger.warning(f"加载记忆{file_path}时出错: {e}")                         
                            continue

                        self.memory_data[token_name] = {
                            'memory': deque(memory_data['memory']),
                            'total_length': memory_data['total_length'],
                            'memory_summary': memory_data['memory_summary'],
                            'summary_embeddings': [np.array(embedding) for embedding in memory_data['summary_embeddings']],
                            'embeddings': deque([np.array(embedding) for embedding in memory_data['embeddings']])
                        }
                    logger.info(f"记忆已从 {file_path} 加载")

        except Exception as e:
            logger.warning(f"加载记忆时出错: {e}")
            

if __name__ == '__main__':
    from sentence_transformers import SentenceTransformer
    # 示例使用
    embedding_model = SentenceTransformer('jinaai/jina-embeddings-v2-base-zh', trust_remote_code=True, device="cpu")
    memory_manager = MemoryManager(llm=None, embedding_model=embedding_model, max_memory_length=100)

    # 模拟两段对话
    chat_paragraph1 = [
        {"role": "user", "content": "吹到了你的发。😔"},
        {"role": "assistant", "content": "发丝轻拂，独怜此际，梦断谁家？😔"}
    ]

    chat_paragraph2 = [
        {"role": "user", "content": "今天天气。😔"},
        {"role": "assistant", "content": "晴天？😔"}
    ]

    # 添加第一段聊天
    asyncio.run(memory_manager.add_chat_paragraph("user1", chat_paragraph1))

    # 添加第二段聊天
    asyncio.run(memory_manager.add_chat_paragraph("user1", chat_paragraph2))

    # 使用嵌入进行记忆查询
    query = "今天天气?"
    similar_memory = memory_manager.search_memory("user1", query, threshold=0.5)
    print("最相似的记忆内容：", [msg['content'] for msg in similar_memory])

    # 使用嵌入进行记忆总结查询
    similar_summary = memory_manager.search_memory_summary("user1", query, threshold=0.5)
    print("最相似的记忆总结：", similar_summary)
