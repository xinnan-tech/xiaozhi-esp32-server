"""
FTS5检索器实现
"""
from datetime import datetime
from typing import List
from memories.base import BaseMemory
from stores.sqlite_store import SQLiteStore
from utils.tokenizer import tokenize_to_string


class FTS5Retriever:
    """SQLite FTS5 + BM25 检索器"""

    def __init__(self, store: SQLiteStore):
        self.store = store

    async def retrieve(
        self,
        query: str,
        user_id: str,
        top_k: int = 10
    ) -> List[BaseMemory]:
        """
        FTS5 + BM25 检索

        Args:
            query: 查询文本
            user_id: 用户ID
            top_k: 返回结果数量

        Returns:
            记忆列表（按相关性排序）
        """
        # 对查询进行分词
        query_tokens = tokenize_to_string(query)

        # 使用FTS5 + BM25检索
        results = self.store.search_fts(query_tokens, user_id, top_k * 2)

        # 多因素加权排序
        scored_results = []
        current_time = datetime.now()

        for memory, bm25_score in results:
            # 基础BM25分数（归一化到0-1）
            # BM25分数通常是负数，越小越好
            base_score = max(0, 1 + bm25_score / 10) if bm25_score else 0.5

            # 时间衰减
            days_ago = (current_time - memory.created_at).days
            time_decay = 1.0 / (1.0 + days_ago / 30.0)  # 30天半衰期

            # 重要性加权
            importance_boost = memory.importance * 0.2

            # 访问频率加权
            access_boost = min(memory.access_count * 0.05, 0.3)

            # 综合分数
            final_score = (
                base_score * 0.5 +
                time_decay * 0.2 +
                importance_boost +
                access_boost
            )

            scored_results.append((memory, final_score))

        # 排序返回
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [m for m, s in scored_results[:top_k]]
