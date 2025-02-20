import threading
import numpy as np
import logging
from config.logger import setup_logging

logger = setup_logging()
TAG = __name__

class IntentResult:
    """
    结果类，用于封装意图识别的结果信息
    """
    def __init__(self, success: bool, intent: str = None, similarity: float = 0.0, response=None):
        """
        :param success: 是否成功匹配到意图
        :param intent: 匹配到的意图短语（若匹配失败为 None）
        :param similarity: 匹配时的相似度
        :param response: 回调函数执行后的返回值
        """
        self.success = success
        self.intent = intent
        self.similarity = similarity
        self.response = response

    def __repr__(self):
        return f"Result(success={self.success}, intent={self.intent}, similarity={self.similarity:.2f}, response={self.response})"


class IntentRecognizer:
    intent_embeddings_cache = {}
    cache_lock = threading.Lock()

    def __init__(self, embedding_model):
        self.embedding_model = embedding_model
        # 存储注册的意图及其相似度阈值和对应的回调函数
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
                # 如果该短语的嵌入已缓存，则直接使用缓存
                if phrase not in IntentRecognizer.intent_embeddings_cache:
                    # 计算嵌入并缓存
                    intent_embedding = self.embedding_model.encode([phrase])[0]
                    IntentRecognizer.intent_embeddings_cache[phrase] = intent_embedding
                else:
                    # 使用缓存的嵌入
                    intent_embedding = IntentRecognizer.intent_embeddings_cache[phrase]

                # 存储意图短语、回调函数和相似度阈值
                self.intent_callbacks.append({
                    "phrase": phrase,
                    "embedding": intent_embedding,
                    "callback": callback_function,
                    "threshold": similarity_threshold
                })

    def handle_query(self, query: str, *args, **kwargs) -> IntentResult:
        """
        处理用户查询并进行意图识别，调用匹配的回调函数
        :param query: 用户查询
        :param args: 传递给回调函数的位置参数
        :param kwargs: 传递给回调函数的关键字参数
        :return: Result 类实例，封装识别结果和回调函数返回值
        """
        query = query.strip()
        # 计算查询的嵌入表示
        query_embedding = self.embedding_model.encode([query])[0]

        best_match = None
        highest_similarity = -1
        matched_callback = None

        # 遍历注册的意图，比较查询与意图短语的相似度
        for intent in self.intent_callbacks:
            similarity = np.dot(query_embedding, intent["embedding"]) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(intent["embedding"])
            )
            if similarity > highest_similarity and similarity >= intent["threshold"]:
                highest_similarity = similarity
                best_match = intent["phrase"]
                matched_callback = intent["callback"]

        if best_match and matched_callback:
            logger.bind(tag=TAG).info(f"{query}\t意图识别结果：{best_match}\tfunc:{matched_callback}\t (相似度: {highest_similarity:.2f})")
            
            response = matched_callback(query, *args, **kwargs)
            return IntentResult(success=True, intent=best_match, similarity=highest_similarity, response=response)

        logger.bind(tag=TAG).info(f"{query}\t未识别到意图")

        return IntentResult(success=False, intent=None, similarity=highest_similarity, response=None)
