# 小智记忆框架设计 (XiaoZhi Memory Framework)

## 设计理念

综合 **mem0ai**、**PowerMem**、**LangMem**、**MemGPT**、**Cognee**、**MemOS** 的优点，为小智ESP32服务器设计一个轻量级、高效的记忆系统。

---

## 核心设计原则

1. **轻量优先**: 适合嵌入式设备部署
2. **中文友好**: 原生支持中文，保持原文语言
3. **智能管理**: 支持记忆的增删改查和遗忘
4. **意图感知**: 专门处理未来计划和意图
5. **渐进式**: 可从简单开始，逐步添加高级功能
6. **双模式支持**: 支持 Embedding 和 非 Embedding 两种检索模式

---

## 系统架构

```
xiaozhi-memory/
├── core/
│   ├── memory_manager.py      # 核心记忆管理器
│   ├── memory_store.py        # 存储抽象层
│   └── retriever/
│       ├── base.py            # 检索器基类
│       ├── embedding.py       # Embedding检索器
│       └── fts.py             # FTS5检索器
├── prompts/
│   ├── extraction.py          # 事实提取提示词
│   ├── update.py              # 记忆更新提示词
│   └── intention.py           # 意图识别提示词
├── stores/
│   ├── base.py                # 存储基类
│   ├── sqlite_store.py        # SQLite存储（FTS5）
│   ├── vector_store.py        # 向量存储（ChromaDB/Qdrant）
│   └── profile_store.py       # 用户画像存储
├── memories/
│   ├── base.py                # 基础记忆类
│   ├── fact.py                # 事实记忆
│   ├── intention.py           # 意图记忆
│   └── profile.py             # 用户画像
├── utils/
│   ├── time_parser.py         # 时间解析器
│   ├── language_detector.py   # 语言检测
│   ├── deduplicator.py        # 去重器
│   └── tokenizer.py           # 中文分词（jieba）
└── api/
    ├── __init__.py            # 统一API入口
    └── rest_api.py            # REST API（可选）
```

---

## 数据模型

### 1. 基础记忆 (BaseMemory)

```python
from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel

class MemoryType(str, Enum):
    FACT = "fact"           # 事实记忆
    INTENTION = "intention" # 意图记忆
    PREFERENCE = "preference" # 偏好记忆
    PROFILE = "profile"     # 用户画像

class MemoryStatus(str, Enum):
    ACTIVE = "active"       # 活跃
    ARCHIVED = "archived"   # 归档
    DELETED = "deleted"     # 删除

class IntentionStatus(str, Enum):
    PLANNED = "planned"     # 计划中
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed" # 已完成
    CANCELLED = "cancelled" # 已取消

class BaseMemory(BaseModel):
    id: str
    user_id: str
    type: MemoryType
    content: str
    original_language: str  # 原始语言（不翻译）
    created_at: datetime
    updated_at: datetime
    status: MemoryStatus = MemoryStatus.ACTIVE
    importance: float = 0.5  # 重要性分数 0-1
    access_count: int = 0    # 访问次数
    last_accessed: Optional[datetime] = None

    # 向量检索相关（可选）
    embedding: Optional[List[float]] = None

    # FTS5检索相关
    tokens: Optional[List[str]] = None  # 分词结果

    # 关联记忆（类似mem0ai的linked_memory_ids）
    related_ids: List[str] = []

    # 元数据
    metadata: dict = {}
```

### 2. 事实记忆 (FactMemory)

```python
class FactMemory(BaseMemory):
    type: MemoryType = MemoryType.FACT

    # 时间信息
    time_info: Optional[dict] = None  # {"absolute": "2025-05-22", "relative": "两天后"}

    # 事实类型
    fact_type: Optional[str] = None  # personal, professional, health, etc.

    # 置信度
    confidence: float = 1.0  # 0-1
```

### 3. 意图记忆 (IntentionMemory)

```python
class IntentionMemory(BaseMemory):
    type: MemoryType = MemoryType.INTENTION

    # 意图状态
    intention_status: IntentionStatus = IntentionStatus.PLANNED

    # 时间信息
    planned_time: Optional[datetime] = None  # 计划时间（绝对时间）
    time_description: Optional[str] = None   # 原始时间描述（"两天后"）

    # 意图类型
    intention_type: Optional[str] = None  # meeting, travel, task, purchase, etc.

    # 提醒设置
    reminder_sent: bool = False
    reminder_time: Optional[datetime] = None

    # 完成信息
    completed_at: Optional[datetime] = None
```

### 4. 用户画像 (UserProfile)

```python
class UserProfile(BaseMemory):
    type: MemoryType = MemoryType.PROFILE

    # 用户基本信息
    name: Optional[str] = None
    nickname: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None

    # 偏好汇总
    preferences: dict = {}  # {"food": ["辣", "海鲜"], "music": ["古典", "爵士"]}

    # 关系网络
    relationships: dict = {}  # {"家人": ["妈妈", "爸爸"], "朋友": ["张三"]}

    # 统计信息
    total_memories: int = 0
    last_interaction: Optional[datetime] = None
```

---

## 核心提示词设计

### 1. 事实提取提示词 (参考 PowerMem + mem0ai)

```python
FACT_EXTRACTION_PROMPT = """你是一个个人信息提取助手。从对话中提取相关事实、记忆、偏好和意图。

CRITICAL 规则:
1. TEMPORAL: 始终提取时间信息。将相对时间转换为绝对时间，同时保留原始时间描述
   - 例如: "两天后" → {"absolute": "2025-05-22", "relative": "两天后"}
2. COMPLETE: 提取完整的事实，包含谁/什么/何时/何地
3. SEPARATE: 不同时间段的事实用分开提取
4. INTENTIONS: 始终提取用户的意图、需求和请求，即使没有时间信息
   - 例如: "我想约个心脏科医生" → 意图记忆
5. LANGUAGE: 不要翻译！保持原文语言
   - 中文输入 → 中文输出
   - 英文输入 → 英文输出

记忆类型:
- FACT: 已发生的事实（"昨天去了北京"）
- INTENTION: 未来的计划和意图（"明天要去开会"）
- PREFERENCE: 偏好（"喜欢喝咖啡"）

输出格式:
{{
  "facts": [
    {{
      "content": "记忆内容（保持原文语言）",
      "type": "FACT|INTENTION|PREFERENCE",
      "time_info": {{"absolute": "2025-05-22", "relative": "两天后"}},
      "intention_type": "meeting|travel|task|purchase|...",
      "importance": 0.8
    }}
  ]
}}

今天的日期: {current_date}

从以下对话中提取信息:
{conversation}
"""
```

### 2. 记忆更新提示词 (参考 PowerMem)

```python
MEMORY_UPDATE_PROMPT = """你是一个记忆管理器。比较新事实与现有记忆，决定操作类型。

操作类型:
1. ADD: 新信息 → 添加新记忆
2. UPDATE: 信息已存在但有更新 → 更新记忆
3. DELETE: 信息矛盾 → 删除旧记忆
4. NONE: 已存在且相同 → 无操作

时间规则 (CRITICAL):
- 新事实有时间，旧记忆没有 → UPDATE 添加时间
- 都有时间，新的更具体/最近 → UPDATE 到新时间
- 时间冲突 → UPDATE 到更近的时间
- 保留相对时间引用

意图状态规则:
- 计划改变 → UPDATE intention_status
- 取消计划 → UPDATE 为 cancelled
- 完成计划 → UPDATE 为 completed

多语言规则 (CRITICAL):
- 不要翻译记忆内容
- 保持原有语言

输出格式:
{{
  "operations": [
    {{
      "id": "记忆ID（UPDATE/DELETE用现有ID，ADD用新ID）",
      "operation": "ADD|UPDATE|DELETE|NONE",
      "content": "新内容",
      "old_content": "旧内容（UPDATE时需要）",
      "status": "状态变更（如有）"
    }}
  ]
}}

当前记忆:
{current_memories}

新事实:
{new_facts}
"""
```

### 3. 意图识别提示词

```python
INTENTION_RECOGNITION_PROMPT = """你是一个意图识别助手。从用户的陈述中识别未来的计划和意图。

意图类型:
- meeting: 会议/约会
- travel: 旅行/出行
- task: 任务/待办
- purchase: 购物计划
- appointment: 预约/挂号
- learning: 学习计划
- other: 其他

CRITICAL 规则:
1. 提取时间信息（相对→绝对转换）
2. 识别意图类型
3. 保持原文语言

输出格式:
{{
  "intentions": [
    {{
      "content": "意图描述",
      "type": "meeting|travel|task|...",
      "planned_time": "2025-05-22T10:00:00",
      "time_description": "明天上午10点",
      "priority": "high|medium|low"
    }}
  ]
}}

今天的日期: {current_date}

用户陈述:
{user_input}
"""
```

---

## 检索模式设计

系统支持两种检索模式，可根据需求选择：

### 模式对比

| 特性 | Embedding模式 | FTS5模式 |
|------|--------------|---------|
| **检索方式** | 语义向量相似度 | BM25全文检索 |
| **存储** | ChromaDB/Qdrant | SQLite + FTS5 |
| **依赖** | 需要Embedding模型 | 无需额外模型 |
| **中文支持** | 需要中文Embedding模型 | 需要jieba分词器 |
| **语义理解** | ✅ 理解同义词、语义相似 | ❌ 仅关键词匹配 |
| **性能** | 较慢（需计算向量） | 快速（内置索引） |
| **准确率** | 高（语义理解） | 中（关键词匹配） |
| **部署复杂度** | 中 | 低 |
| **成本** | API调用或本地模型 | 无 |
| **适用场景** | 语义搜索、复杂查询 | 简单关键词、资源受限 |

### 选择建议

**选择 Embedding 模式**：
- 需要语义理解（如"我想吃点好吃的"能找到"餐厅"记忆）
- 有足够资源部署Embedding模型
- 对检索准确率要求高

**选择 FTS5 模式**：
- 资源受限（无GPU/内存有限）
- 主要进行关键词搜索
- 需要最快的响应速度
- 离线部署

---

## 存储层设计

### 1. SQLite + FTS5 存储（推荐用于轻量级部署）

```python
import sqlite3
import jieba
from typing import List, Optional
from datetime import datetime

class SQLiteStore:
    """SQLite + FTS5 全文检索存储"""

    def __init__(self, db_path: str = "./data/xiaozhi_memory.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        """初始化表结构"""

        # 主表：存储记忆
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                original_language TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                time_info TEXT,  -- JSON
                fact_type TEXT,
                intention_status TEXT,
                planned_time TIMESTAMP,
                time_description TEXT,
                intention_type TEXT,
                metadata TEXT,  -- JSON
                related_ids TEXT  -- JSON array
            )
        """)

        # FTS5虚拟表：全文检索
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                id,
                user_id,
                content,
                tokens,
                content='memories',
                content_rowid='rowid',
                tokenize='unicode61'
            )
        """)

        # 创建索引
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_id ON memories(user_id)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_type ON memories(type)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON memories(status)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_planned_time ON memories(planned_time)
        """)

        # 创建触发器：自动同步FTS5表
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, id, user_id, content, tokens)
                VALUES (new.rowid, new.id, new.user_id, new.content, new.tokens);
            END
        """)

        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, id, user_id, content, tokens)
                VALUES ('delete', old.rowid, old.id, old.user_id, old.content, old.tokens);
            END
        """)

        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, id, user_id, content, tokens)
                VALUES ('delete', old.rowid, old.id, old.user_id, old.content, old.tokens);
                INSERT INTO memories_fts(rowid, id, user_id, content, tokens)
                VALUES (new.rowid, new.id, new.user_id, new.content, new.tokens);
            END
        """)

        self.conn.commit()

    def add(self, memory: BaseMemory) -> str:
        """添加记忆"""
        # 中文分词
        tokens = " ".join(jieba.lcut(memory.content))

        self.conn.execute("""
            INSERT INTO memories (
                id, user_id, type, content, original_language,
                created_at, updated_at, status, importance,
                tokens, time_info, fact_type, intention_status,
                planned_time, time_description, intention_type,
                metadata, related_ids
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.id, memory.user_id, memory.type, memory.content,
            memory.original_language, memory.created_at, memory.updated_at,
            memory.status, memory.importance, tokens,
            json.dumps(memory.time_info) if memory.time_info else None,
            memory.fact_type if hasattr(memory, 'fact_type') else None,
            memory.intention_status if hasattr(memory, 'intention_status') else None,
            memory.planned_time if hasattr(memory, 'planned_time') else None,
            memory.time_description if hasattr(memory, 'time_description') else None,
            memory.intention_type if hasattr(memory, 'intention_type') else None,
            json.dumps(memory.metadata),
            json.dumps(memory.related_ids)
        ))
        self.conn.commit()
        return memory.id

    def search_fts(self, query: str, user_id: str, top_k: int = 10) -> List[BaseMemory]:
        """
        使用FTS5 + BM25全文检索

        BM25公式: score = IDF * (f * (k1 + 1)) / (f + k1 * (1 - b + b * D / avgD))

        其中:
        - f: 词频
        - IDF: 逆文档频率
        - k1: 调节词频饱和度 (默认1.2)
        - b: 调节文档长度归一化 (默认0.75)
        """
        # 对查询也进行分词
        query_tokens = " ".join(jieba.lcut(query))

        # 使用BM25排名
        cursor = self.conn.execute(f"""
            SELECT
                m.*,
                bm25(memories_fts) as score
            FROM memories_fts fts
            JOIN memories m ON m.id = fts.id
            WHERE m.user_id = ?
                AND m.status = 'active'
                AND memories_fts MATCH ?
            ORDER BY score
            LIMIT ?
        """, (user_id, query_tokens, top_k))

        results = []
        for row in cursor.fetchall():
            results.append(self._row_to_memory(row))

        return results
```

### 2. 向量存储（用于语义检索）

```python
import chromadb
from chromadb.config import Settings

class VectorStore:
    """ChromaDB 向量存储"""

    def __init__(self, path: str = "./data/chroma"):
        self.client = chromadb.PersistentClient(path=path)
        self.collection = self.client.get_or_create_collection(
            name="xiaozhi_memories",
            metadata={"hnsw:space": "cosine"}
        )

    def add(self, memory: BaseMemory, embedding: List[float]):
        """添加记忆"""
        self.collection.add(
            ids=[memory.id],
            embeddings=[embedding],
            documents=[memory.content],
            metadatas=[{
                "user_id": memory.user_id,
                "type": memory.type,
                "created_at": memory.created_at.isoformat(),
                "importance": memory.importance
            }]
        )

    def search(self, query_embedding: List[float], user_id: str,
               top_k: int = 10) -> List[BaseMemory]:
        """向量相似度搜索"""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": user_id, "status": "active"}
        )

        return results
```

---

## 检索器实现

### 1. FTS5 检索器（无 Embedding）

```python
class FTS5Retriever:
    """SQLite FTS5 + BM25 检索器"""

    def __init__(self, store: SQLiteStore):
        self.store = store

    def retrieve(self, query: str, user_id: str, top_k: int = 10) -> List[BaseMemory]:
        """
        FTS5 + BM25 检索
        优势: 快速、无需Embedding模型
        劣势: 仅关键词匹配，无语义理解
        """
        # 1. BM25全文检索
        results = self.store.search_fts(query, user_id, top_k * 2)

        # 2. 时间衰减 + 重要性加权
        scored_results = []
        current_time = datetime.now()

        for memory in results:
            # 基础BM25分数
            base_score = getattr(memory, 'score', 0)

            # 时间衰减
            days_ago = (current_time - memory.created_at).days
            time_decay = 1.0 / (1.0 + days_ago / 30.0)

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

        # 3. 排序返回
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [m for m, s in scored_results[:top_k]]
```

### 2. Embedding 检索器（语义检索）

```python
class EmbeddingRetriever:
    """向量语义检索器"""

    def __init__(self, store: VectorStore, embedding_model):
        self.store = store
        self.embedding_model = embedding_model

    def retrieve(self, query: str, user_id: str, top_k: int = 10) -> List[BaseMemory]:
        """
        语义向量检索
        优势: 理解语义、同义词
        劣势: 需要Embedding模型
        """
        # 1. 生成查询向量
        query_embedding = self.embedding_model.encode(query)

        # 2. 向量相似度搜索
        results = self.store.search(query_embedding, user_id, top_k * 2)

        # 3. 多因素加权排序
        scored_results = []
        current_time = datetime.now()

        for memory, similarity in results:
            # 时间衰减
            days_ago = (current_time - memory.created_at).days
            time_decay = 1.0 / (1.0 + days_ago / 30.0)

            # 重要性加权
            importance_boost = memory.importance * 0.2

            # 综合分数
            final_score = (
                similarity * 0.6 +
                time_decay * 0.2 +
                importance_boost
            )

            scored_results.append((memory, final_score))

        # 4. 排序返回
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return [m for m, s in scored_results[:top_k]]
```

### 3. 混合检索器（Embedding + FTS5）

```python
class HybridRetriever:
    """混合检索器: 结合语义和关键词"""

    def __init__(self, sqlite_store: SQLiteStore,
                 vector_store: VectorStore,
                 embedding_model):
        self.sqlite_store = sqlite_store
        self.vector_store = vector_store
        self.embedding_model = embedding_model

        self.fts_retriever = FTS5Retriever(sqlite_store)
        self.embedding_retriever = EmbeddingRetriever(vector_store, embedding_model)

    def retrieve(self, query: str, user_id: str,
                top_k: int = 10,
                semantic_weight: float = 0.7) -> List[BaseMemory]:
        """
        混合检索: RRF (Reciprocal Rank Fusion)

        Args:
            query: 查询文本
            user_id: 用户ID
            top_k: 返回结果数量
            semantic_weight: 语义检索权重 (0-1)
                              1.0 = 纯语义
                              0.0 = 纯关键词
                              0.7 = 默认，语义为主
        """
        keyword_weight = 1.0 - semantic_weight

        # 1. 并行检索
        semantic_results = self.embedding_retriever.retrieve(query, user_id, top_k * 2)
        keyword_results = self.fts_retriever.retrieve(query, user_id, top_k * 2)

        # 2. RRF融合
        fused_scores = {}

        # 语义检索分数
        for i, memory in enumerate(semantic_results):
            score = semantic_weight / (i + 1)  # RRF公式
            fused_scores[memory.id] = fused_scores.get(memory.id, 0) + score

        # 关键词检索分数
        for i, memory in enumerate(keyword_results):
            score = keyword_weight / (i + 1)
            fused_scores[memory.id] = fused_scores.get(memory.id, 0) + score

        # 3. 排序返回
        memory_map = {m.id: m for m in semantic_results + keyword_results}
        sorted_ids = sorted(fused_scores.keys(),
                           key=lambda x: fused_scores[x],
                           reverse=True)

        return [memory_map[id] for id in sorted_ids[:top_k]]
```

---

## 多信号检索 (更新版)

```python
class MemoryRetriever:
    """多信号记忆检索器"""

    def __init__(self, vector_store, bm25_index=None):
        self.vector_store = vector_store
        self.bm25_index = bm25_index

    def retrieve(self, query: str, user_id: str, top_k: int = 10) -> List[BaseMemory]:
        """
        多信号融合检索:
        1. 语义搜索 (向量)
        2. 关键词搜索 (BM25)
        3. 时间衰减
        4. 重要性加权
        """

        # 1. 语义搜索
        semantic_results = self.vector_store.search(query, user_id, top_k * 2)

        # 2. 关键词搜索 (如果有BM25索引)
        if self.bm25_index:
            keyword_results = self.bm25_index.search(query, user_id, top_k * 2)
        else:
            keyword_results = []

        # 3. 融合排序
        fused_scores = {}
        current_time = datetime.now()

        # 语义搜索分数
        for i, memory in enumerate(semantic_results):
            score = 1.0 / (i + 1)  # 倒数排名融合
            fused_scores[memory.id] = fused_scores.get(memory.id, 0) + score * 0.6

        # 关键词搜索分数
        for i, memory in enumerate(keyword_results):
            score = 1.0 / (i + 1)
            fused_scores[memory.id] = fused_scores.get(memory.id, 0) + score * 0.3

        # 时间衰减 + 重要性
        for memory in semantic_results + keyword_results:
            if memory.id not in fused_scores:
                continue

            # 时间衰减: 越近的记忆分数越高
            days_ago = (current_time - memory.created_at).days
            time_decay = 1.0 / (1.0 + days_ago / 30.0)  # 30天半衰期

            # 重要性加权
            importance_boost = memory.importance

            fused_scores[memory.id] += time_decay * 0.05 + importance_boost * 0.05

        # 排序返回
        sorted_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
        result_ids = sorted_ids[:top_k]

        return [self.get_memory_by_id(id) for id in result_ids]
```

---

## 记忆管理器（更新版）

```python
from enum import Enum

class RetrievalMode(str, Enum):
    FTS5 = "fts5"           # 纯FTS5检索
    EMBEDDING = "embedding" # 纯向量检索
    HYBRID = "hybrid"       # 混合检索

class MemoryManager:
    """核心记忆管理器 - 支持多种检索模式"""

    def __init__(self, config: dict):
        self.config = config
        self.mode = RetrievalMode(config.get("retrieval_mode", "fts5"))

        # 根据模式初始化存储
        if self.mode in [RetrievalMode.FTS5, RetrievalMode.HYBRID]:
            self.sqlite_store = SQLiteStore(config["sqlite"]["path"])

        if self.mode in [RetrievalMode.EMBEDDING, RetrievalMode.HYBRID]:
            self.vector_store = VectorStore(config["vector_store"]["path"])
            self.embedding_model = self._init_embedding_model(config["embedding"])

        # 初始化检索器
        self.retriever = self._init_retriever()

        # LLM客户端
        self.llm = self._init_llm(config["llm"])

    def _init_retriever(self):
        """根据模式初始化检索器"""
        if self.mode == RetrievalMode.FTS5:
            return FTS5Retriever(self.sqlite_store)
        elif self.mode == RetrievalMode.EMBEDDING:
            return EmbeddingRetriever(self.vector_store, self.embedding_model)
        elif self.mode == RetrievalMode.HYBRID:
            return HybridRetriever(
                self.sqlite_store,
                self.vector_store,
                self.embedding_model
            )

    async def add_memory(self, messages: List[dict], user_id: str) -> dict:
        """
        添加记忆流程:
        1. 提取事实（FACT_EXTRACTION_PROMPT）
        2. 检测语言
        3. 去重
        4. 生成向量（如果需要）
        5. 存储
        """
        # 1. 提取事实
        facts = await self._extract_facts(messages)

        results = {"added": 0, "updated": 0, "skipped": 0}

        for fact in facts:
            # 检查是否已存在
            existing = await self._find_similar(fact["content"], user_id)

            if existing:
                # 更新
                await self._update_memory(existing.id, fact)
                results["updated"] += 1
            else:
                # 创建记忆对象
                memory = self._create_memory(fact, user_id)

                # 生成向量（如果需要）
                if self.mode in [RetrievalMode.EMBEDDING, RetrievalMode.HYBRID]:
                    memory.embedding = await self.embedding_model.encode(memory.content)

                # 存储
                if self.mode in [RetrievalMode.FTS5, RetrievalMode.HYBRID]:
                    self.sqlite_store.add(memory)
                if self.mode in [RetrievalMode.EMBEDDING, RetrievalMode.HYBRID]:
                    self.vector_store.add(memory, memory.embedding)

                results["added"] += 1

        return results

    async def search(self, query: str, user_id: str, top_k: int = 10) -> List[BaseMemory]:
        """搜索记忆 - 使用配置的检索器"""
        return await self.retriever.retrieve(query, user_id, top_k)

    async def get_upcoming_intentions(self, user_id: str, days: int = 7) -> List[IntentionMemory]:
        """获取未来N天的意图/计划"""
        now = datetime.now()
        future = now + timedelta(days=days)

        # 使用SQLite查询（结构化查询更高效）
        return await self.sqlite_store.get_intentions_in_range(user_id, now, future)

    async def update_intention_status(self, memory_id: str, status: IntentionStatus):
        """更新意图状态"""
        await self.sqlite_store.update(memory_id, {
            "intention_status": status,
            "completed_at": datetime.now() if status == IntentionStatus.COMPLETED else None
        })
```

---

## 用户画像管理 (参考 PowerMem)

```python
class UserProfileManager:
    """用户画像管理器"""

    async def update_profile(self, user_id: str, memories: List[BaseMemory]):
        """
        从记忆中更新用户画像:
        1. 统计偏好
        2. 提取关系
        3. 更新统计
        """
        profile = await self.store.get_profile(user_id)

        # 统计偏好
        preferences = {}
        relationships = {}

        for memory in memories:
            if memory.type == MemoryType.PREFERENCE:
                # 提取偏好
                pass
            elif memory.type == MemoryType.FACT:
                # 提取关系
                pass

        profile.preferences = preferences
        profile.relationships = relationships
        profile.total_memories = len(memories)
        profile.last_interaction = datetime.now()

        await self.store.update_profile(profile)
```

---

## 遗忘机制 (参考 PowerMem 艾宾浩斯曲线)

```python
class ForgettingCurve:
    """艾宾浩斯遗忘曲线"""

    @staticmethod
    def retention_score(days_ago: int, importance: float) -> float:
        """
        计算记忆保留分数

        R(t) = importance * e^(-t/S)

        t: 天数
        S: 记忆强度（默认30天）
        """
        S = 30  # 记忆强度
        return importance * math.exp(-days_ago / S)

    @staticmethod
    def should_archive(memory: BaseMemory) -> bool:
        """判断是否应该归档记忆"""
        if memory.type == MemoryType.INTENTION:
            # 已完成的意图，30天后归档
            if memory.intention_status == IntentionStatus.COMPLETED:
                return (datetime.now() - memory.completed_at).days > 30
            # 已取消的意图，7天后归档
            if memory.intention_status == IntentionStatus.CANCELLED:
                return (datetime.now() - memory.updated_at).days > 7

        # 其他记忆，根据遗忘曲线
        days_ago = (datetime.now() - memory.last_accessed or memory.created_at).days
        retention = ForgettingCurve.retention_score(days_ago, memory.importance)

        return retention < 0.1  # 保留分数低于10%归档
```

---

## REST API 接口 (参考 PowerMem Benchmark Server)

```python
from fastapi import FastAPI, HTTPException

app = FastAPI(title="小智记忆API")

@app.post("/memories")
async def add_memory(request: MemoryCreate):
    """添加记忆"""
    manager = get_memory_manager()
    result = await manager.add_memory(request.messages, request.user_id)
    return result

@app.get("/memories")
async def get_memories(user_id: str):
    """获取所有记忆"""
    store = get_store()
    return await store.get_by_user(user_id)

@app.post("/search")
async def search(request: SearchRequest):
    """搜索记忆"""
    manager = get_memory_manager()
    results = await manager.search(request.query, request.user_id, request.top_k)
    return {"memories": results}

@app.get("/intentions")
async def get_upcoming_intentions(user_id: str, days: int = 7):
    """获取未来计划"""
    manager = get_memory_manager()
    return await manager.get_upcoming_intentions(user_id, days)

@app.put("/memories/{memory_id}/status")
async def update_intention_status(memory_id: str, status: IntentionStatus):
    """更新意图状态"""
    manager = get_memory_manager()
    await manager.update_intention_status(memory_id, status)
    return {"message": "Status updated"}
```

---

## 配置示例

```yaml
# config.yaml
memory:
  # 检索模式选择: fts5, embedding, hybrid
  retrieval_mode: fts5  # 默认使用FTS5（轻量级）

  # SQLite + FTS5 配置
  sqlite:
    path: ./data/xiaozhi_memory.db
    enable_wal: true  # 启用WAL模式提升并发性能
    tokenizer: jieba  # 中文分词器: jieba, simple, unicode61

  # 向量存储配置（可选，embedding模式需要）
  vector_store:
    type: chromadb  # chromadb, qdrant
    path: ./data/chroma
    collection_name: xiaozhi_memories

  # LLM配置
  llm:
    provider: openai  # openai, ollama, zhipu
    model: gpt-4o-mini
    api_key: ${OPENAI_API_KEY}
    base_url: ${LLM_BASE_URL}  # 可选

  # 嵌入模型配置（可选，embedding模式需要）
  embedding:
    provider: openai  # openai, sentence-transformers, zhipu
    model: text-embedding-3-small
    # 或本地模型（推荐）
    # provider: sentence-transformers
    # model: /models/paraphrase-multilingual-MiniLM-L12-v2
    # device: cpu  # cpu, cuda

  # 记忆配置
  retention:
    enabled: true  # 启用遗忘机制
    archive_after_days: 90

  # 用户画像
  profile:
    enabled: true
    auto_update: true

  # 检索配置
  retrieval:
    top_k: 10
    # 混合模式权重
    semantic_weight: 0.7  # 语义检索权重
    keyword_weight: 0.3   # 关键词检索权重
    # 时间和重要性
    time_decay: true
    importance_boost: true
    access_boost: true
```

### 模式配置示例

#### 模式1: 纯FTS5（最轻量）

```yaml
memory:
  retrieval_mode: fts5
  sqlite:
    path: ./data/xiaozhi_memory.db
  llm:
    provider: ollama
    model: qwen2:7b
```

#### 模式2: 纯Embedding（语义理解）

```yaml
memory:
  retrieval_mode: embedding
  vector_store:
    type: chromadb
    path: ./data/chroma
  embedding:
    provider: sentence-transformers
    model: /models/paraphrase-multilingual-MiniLM-L12-v2
  llm:
    provider: ollama
    model: qwen2:7b
```

#### 模式3: 混合模式（最佳效果）

```yaml
memory:
  retrieval_mode: hybrid
  sqlite:
    path: ./data/xiaozhi_memory.db
  vector_store:
    type: chromadb
    path: ./data/chroma
  embedding:
    provider: sentence-transformers
    model: /models/paraphrase-multilingual-MiniLM-L12-v2
  retrieval:
    semantic_weight: 0.7
    keyword_weight: 0.3
```

---

## 渐进式实现路线

### Phase 1: 基础功能 - FTS5模式 (MVP)
**目标**: 最小可用产品，纯本地部署
- [x] SQLite + FTS5 存储
- [x] 基础记忆模型 (FactMemory)
- [x] jieba 中文分词
- [x] BM25 全文检索
- [x] ADD/SEARCH 操作
- [x] 中文支持

**优势**:
- 无需额外依赖
- 无需API调用
- 响应速度快
- 适合离线部署

### Phase 2: 智能管理
- [x] UPDATE/DELETE 操作
- [x] 事实提取提示词
- [x] 去重机制
- [x] 时间衰减排序
- [x] 重要性加权

### Phase 3: 意图管理
- [x] IntentionMemory
- [x] 时间解析（相对→绝对）
- [x] 意图状态管理
- [x] 未来计划查询

### Phase 4: Embedding模式 (可选)
- [ ] 本地Embedding模型 (sentence-transformers)
- [ ] ChromaDB 向量存储
- [ ] 语义检索
- [ ] 混合检索 (HybridRetriever)

**何时升级**:
- 需要语义理解
- 关键词检索不够用
- 有额外资源部署模型

### Phase 5: 高级功能
- [ ] 用户画像
- [ ] 遗忘机制
- [ ] 记忆关联图
- [ ] 提醒功能

### Phase 6: 企业功能
- [ ] 多用户隔离
- [ ] 权限管理
- [ ] 数据导出
- [ ] REST API

---

## 与现有系统集成

### 小智ESP32服务器集成

```python
# main/xiaozhi-server/core/providers/memory/xiaozhi_mem.py

from .base import MemoryProviderBase

class MemoryProvider(MemoryProviderBase):
    def __init__(self, config):
        super().__init__(config)
        from xiaozhi_memory import MemoryManager

        self.manager = MemoryManager(config)

    async def save_memory(self, msgs, session_id=None):
        """保存对话记录"""
        # 转换消息格式
        messages = [{"role": m.role, "content": m.content} for m in msgs]

        # 添加记忆
        result = await self.manager.add_memory(messages, self.role_id)
        logger.bind(tag=TAG).info(f"记忆保存: {result}")

    async def query_memory(self, query: str) -> str:
        """查询相关记忆"""
        if not self.role_id:
            return ""

        # 搜索记忆
        memories = await self.manager.search(query, self.role_id, top_k=5)

        # 格式化返回
        return self._format_memories(memories)

    async def get_upcoming_plans(self) -> str:
        """获取未来计划（新功能）"""
        if not self.role_id:
            return ""

        intentions = await self.manager.get_upcoming_intentions(self.role_id, days=7)

        if not intentions:
            return "用户没有未来计划"

        formatted = []
        for intent in intentions:
            formatted.append(f"- {intent.content} (计划时间: {intent.planned_time})")

        return "用户的未来计划:\n" + "\n".join(formatted)
```

---

## 总结

小智记忆框架 (XiaoZhi Memory Framework) 综合了各开源系统的优点：

| 来源 | 采用特性 |
|------|----------|
| **mem0ai** | 多信号检索、记忆关联、时间解析 |
| **PowerMem** | CRUD操作、多语言保持、意图提取强调 |
| **LangMem** | 模块化设计、提示词优化（预留） |
| **MemGPT** | 分层记忆概念（简化版） |
| **Cognee** | 类型化记忆、知识图谱（预留） |
| **MemOS** | 状态管理、三态记忆 |
| **SQLite FTS5** | BM25全文检索、轻量级部署 |

### 核心优势

1. ✅ **轻量级优先**: 默认使用 SQLite + FTS5，无需额外依赖
2. ✅ **中文友好**: jieba 分词 + 保持原文语言
3. ✅ **智能管理**: 支持增删改查和遗忘机制
4. ✅ **意图感知**: 专门处理未来计划和状态管理
5. ✅ **渐进式**: 从 FTS5 开始，可升级到 Embedding
6. ✅ **可扩展**: 预留混合检索和高级功能接口

### 检索模式选择建议

| 场景 | 推荐模式 | 理由 |
|------|----------|------|
| **离线部署** | FTS5 | 无需外部依赖 |
| **资源受限** | FTS5 | 内存占用小 |
| **关键词搜索** | FTS5 | 精确匹配，速度快 |
| **语义理解** | Embedding | 理解同义词、意图 |
| **最佳效果** | Hybrid | 结合两者优点 |
| **渐进升级** | FTS5 → Hybrid | 从简单开始 |

### FTS5 vs BM25 vs Embedding

| 特性 | FTS5 + BM25 | Embedding |
|------|-------------|-----------|
| **部署** | 单文件SQLite | 需要向量数据库 |
| **依赖** | jieba分词 | Embedding模型 |
| **语义理解** | ❌ 仅关键词 | ✅ 语义相似 |
| **中文支持** | ✅ jieba | 需中文模型 |
| **速度** | ⚡ 很快 | 较慢 |
| **准确率** | 中等 | 高 |
| **成本** | 免费 | API或本地计算 |

### 推荐配置

**起步阶段（MVP）**:
```yaml
retrieval_mode: fts5
# 只需SQLite + jieba
```

**生产阶段**:
```yaml
retrieval_mode: hybrid
# 结合语义和关键词，效果最佳
```

---

## 参考资料

- [SQLite FTS5 官方文档](https://sqlite.org/fts5.html)
- [SQLite FTS5实战教程](https://blog.csdn.net/echo99/article/details/150481272)
- [BM25算法详解](https://en.wikipedia.org/wiki/Okapi_BM25)
- [jieba中文分词](https://github.com/fxsjy/jieba)
- [mem0ai](https://github.com/mem0ai/mem0)
- [PowerMem](https://github.com/oceanbase/powermem)
- [LangMem](https://github.com/langchain-ai/langmem)
- [MemGPT/Letta](https://github.com/cpacker/MemGPT)
- [Cognee](https://github.com/topoteretes/cognee)
- [MemOS](https://github.com/MemTensor/MemOS)
