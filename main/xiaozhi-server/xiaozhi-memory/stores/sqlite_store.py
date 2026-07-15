"""
存储层基类和SQLite实现
"""
import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from abc import ABC, abstractmethod

from memories.base import BaseMemory, MemoryType, MemoryStatus, IntentionMemory, IntentionStatus


class BaseStore(ABC):
    """存储基类"""

    @abstractmethod
    def add(self, memory: BaseMemory) -> str:
        """添加记忆"""
        pass

    @abstractmethod
    def get(self, memory_id: str) -> Optional[BaseMemory]:
        """获取记忆"""
        pass

    @abstractmethod
    def update(self, memory_id: str, data: Dict[str, Any]) -> bool:
        """更新记忆"""
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        pass

    @abstractmethod
    def get_by_user(self, user_id: str) -> List[BaseMemory]:
        """获取用户所有记忆"""
        pass

    @abstractmethod
    def search_fts(self, query: str, user_id: str, top_k: int) -> List[tuple]:
        """全文检索"""
        pass

    @abstractmethod
    def get_intentions_in_range(self, user_id: str, start: datetime, end: datetime) -> List[IntentionMemory]:
        """获取时间范围内的意图"""
        pass


class SQLiteStore(BaseStore):
    """SQLite + FTS5 存储"""

    def __init__(self, db_path: str = "./data/xiaozhi_memory.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # 返回字典格式
        self._init_tables()

    def _init_tables(self):
        """初始化表结构"""

        # 主表：存储记忆
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                user_id TEXT,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                original_language TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,
                embedding BLOB,
                tokens TEXT,
                related_ids TEXT,
                metadata TEXT,
                time_info TEXT,
                fact_type TEXT,
                confidence REAL DEFAULT 1.0,
                intention_status TEXT,
                planned_time TIMESTAMP,
                time_description TEXT,
                intention_type TEXT,
                reminder_sent INTEGER DEFAULT 0,
                reminder_time TIMESTAMP,
                completed_at TIMESTAMP,
                preference_type TEXT,
                preference_value TEXT,
                name TEXT,
                nickname TEXT,
                age INTEGER,
                location TEXT,
                preferences TEXT,
                relationships TEXT,
                total_memories INTEGER DEFAULT 0,
                last_interaction TIMESTAMP,
                first_met TIMESTAMP,
                total_interaction_days INTEGER DEFAULT 0,
                danger_level TEXT DEFAULT 'low',
                danger_category TEXT DEFAULT 'other',
                severity_score REAL DEFAULT 0.0,
                already_notified INTEGER DEFAULT 0
            )
        """)

        # FTS5虚拟表：全文检索
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                id,
                device_id,
                user_id,
                content,
                tokens,
                content='memories',
                content_rowid='rowid',
                tokenize='unicode61'
            )
        """)

        # 创建索引
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_device_id ON memories(device_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_device_user ON memories(device_id, user_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON memories(user_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON memories(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_planned_time ON memories(planned_time)")

        # 创建触发器：自动同步FTS5表
        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, id, device_id, user_id, content, tokens)
                VALUES (new.rowid, new.id, new.device_id, new.user_id, new.content, new.tokens);
            END
        """)

        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, id, device_id, user_id, content, tokens)
                VALUES ('delete', old.rowid, old.id, old.device_id, old.user_id, old.content, old.tokens);
            END
        """)

        self.conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, id, device_id, user_id, content, tokens)
                VALUES ('delete', old.rowid, old.id, old.device_id, old.user_id, old.content, old.tokens);
                INSERT INTO memories_fts(rowid, id, device_id, user_id, content, tokens)
                VALUES (new.rowid, new.id, new.device_id, new.user_id, new.content, new.tokens);
            END
        """)

        self.conn.commit()

    def add(self, memory: BaseMemory) -> str:
        """添加记忆"""
        # 中文分词（使用 tokenize_to_string 确保 FTS5 安全）
        try:
            from utils.tokenizer import tokenize_to_string
            tokens = tokenize_to_string(memory.content)
        except ImportError:
            tokens = memory.content

        # 根据记忆类型构建不同的 INSERT 语句
        if memory.type.value == "profile":
            # UserProfile 类型，包含所有 profile 字段
            self.conn.execute("""
                INSERT INTO memories (
                    id, device_id, user_id, type, content, original_language,
                    created_at, updated_at, status, importance,
                    tokens, related_ids, metadata, time_info,
                    name, nickname, age, location, preferences, relationships,
                    total_memories, last_interaction, first_met, total_interaction_days
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id,
                memory.device_id,
                memory.user_id,
                memory.type.value,
                memory.content,
                memory.original_language,
                memory.created_at,
                memory.updated_at,
                memory.status.value,
                memory.importance,
                tokens,
                json.dumps(memory.related_ids),
                json.dumps(memory.metadata),
                json.dumps(memory.time_info) if memory.time_info else None,
                getattr(memory, 'name', None),
                getattr(memory, 'nickname', None),
                getattr(memory, 'age', None),
                getattr(memory, 'location', None),
                json.dumps(getattr(memory, 'preferences', {})),
                json.dumps(getattr(memory, 'relationships', {})),
                getattr(memory, 'total_memories', 0),
                getattr(memory, 'last_interaction', None),
                getattr(memory, 'first_met', None),
                getattr(memory, 'total_interaction_days', 0)
            ))
        elif memory.type.value == "danger":
            # DangerMemory 类型
            self.conn.execute("""
                INSERT INTO memories (
                    id, device_id, user_id, type, content, original_language,
                    created_at, updated_at, status, importance,
                    tokens, related_ids, metadata, time_info,
                    danger_level, danger_category, severity_score, already_notified
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id,
                memory.device_id,
                memory.user_id,
                memory.type.value,
                memory.content,
                memory.original_language,
                memory.created_at,
                memory.updated_at,
                memory.status.value,
                memory.importance,
                tokens,
                json.dumps(memory.related_ids),
                json.dumps(memory.metadata),
                json.dumps(memory.time_info) if memory.time_info else None,
                getattr(memory, 'danger_level', 'low'),
                getattr(memory, 'danger_category', 'other'),
                getattr(memory, 'severity_score', 0.0),
                1 if getattr(memory, 'already_notified', False) else 0,
            ))
        else:
            # 其他记忆类型
            self.conn.execute("""
                INSERT INTO memories (
                    id, device_id, user_id, type, content, original_language,
                    created_at, updated_at, status, importance,
                    tokens, related_ids, metadata, time_info,
                    fact_type, confidence,
                    intention_status, planned_time, time_description, intention_type,
                    reminder_sent, reminder_time, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id,
                memory.device_id,
                memory.user_id,
                memory.type.value,
                memory.content,
                memory.original_language,
                memory.created_at,
                memory.updated_at,
                memory.status.value,
                memory.importance,
                tokens,
                json.dumps(memory.related_ids),
                json.dumps(memory.metadata),
                json.dumps(memory.time_info) if memory.time_info else None,
                getattr(memory, 'fact_type', None),
                getattr(memory, 'confidence', 1.0),
                getattr(memory, 'intention_status', None) if hasattr(memory, 'intention_status') else None,
                getattr(memory, 'planned_time', None) if hasattr(memory, 'planned_time') else None,
                getattr(memory, 'time_description', None) if hasattr(memory, 'time_description') else None,
                getattr(memory, 'intention_type', None) if hasattr(memory, 'intention_type') else None,
                getattr(memory, 'reminder_sent', False) if hasattr(memory, 'reminder_sent') else False,
                getattr(memory, 'reminder_time', None) if hasattr(memory, 'reminder_time') else None,
                getattr(memory, 'completed_at', None) if hasattr(memory, 'completed_at') else None
            ))

        self.conn.commit()
        return memory.id

    def get(self, memory_id: str) -> Optional[BaseMemory]:
        """获取记忆"""
        cursor = self.conn.execute(
            "SELECT * FROM memories WHERE id = ?",
            (memory_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_memory(row)

    def update(self, memory_id: str, data: Dict[str, Any]) -> bool:
        """更新记忆"""
        set_clauses = []
        values = []

        for key, value in data.items():
            if key in ['related_ids', 'metadata', 'time_info']:
                value = json.dumps(value)
            set_clauses.append(f"{key} = ?")
            values.append(value)

        if not set_clauses:
            return False

        values.append(datetime.now())  # updated_at
        set_clauses.append("updated_at = ?")

        values.append(memory_id)

        sql = f"UPDATE memories SET {', '.join(set_clauses)} WHERE id = ? AND status != 'deleted'"
        self.conn.execute(sql, values)
        self.conn.commit()
        return self.conn.total_changes > 0

    def delete(self, memory_id: str) -> bool:
        """删除记忆（软删除）"""
        self.conn.execute(
            "UPDATE memories SET status = ? WHERE id = ?",
            (MemoryStatus.DELETED.value, memory_id)
        )
        self.conn.commit()
        return self.conn.total_changes > 0

    def get_by_user(self, user_id: str) -> List[BaseMemory]:
        """获取用户所有活跃记忆（兼容旧接口）"""
        return self.get_by_device(None, user_id)

    def get_by_device(self, device_id: str, user_id: Optional[str] = None) -> List[BaseMemory]:
        """获取设备/用户所有活跃记忆"""
        if user_id:
            cursor = self.conn.execute(
                "SELECT * FROM memories WHERE device_id = ? AND user_id = ? AND status = ? ORDER BY created_at DESC",
                (device_id, user_id, MemoryStatus.ACTIVE.value)
            )
        else:
            # 查询设备级记忆（user_id IS NULL）
            cursor = self.conn.execute(
                "SELECT * FROM memories WHERE device_id = ? AND user_id IS NULL AND status = ? ORDER BY created_at DESC",
                (device_id, MemoryStatus.ACTIVE.value)
            )
        return [self._row_to_memory(row) for row in cursor.fetchall()]

    def search_fts(self, query: str, device_id: str, user_id: Optional[str] = None, top_k: int = 10) -> List[tuple]:
        """
        使用FTS5 + BM25全文检索

        返回: [(memory, score), ...]
        """
        # 使用 tokenize_to_string 清理查询，避免 FTS5 语法错误
        from utils.tokenizer import tokenize_to_string
        safe_query = tokenize_to_string(query)
        if not safe_query:
            return []
        # 用 OR 连接查询词：FTS5 默认空格=AND，含疑问词/虚词的自然语言整句查询
        # （如"我叫什么名字"）会因词不全而全部落空。改 OR 后任一词命中即返回，
        # 由 BM25 排序保证相关性（召回优先于精度，宁多返回交 LLM 判断）。
        or_query = " OR ".join(safe_query.split())

        if user_id:
            cursor = self.conn.execute(f"""
                SELECT
                    m.*,
                    bm25(memories_fts) as score
                FROM memories_fts fts
                JOIN memories m ON m.id = fts.id
                WHERE m.device_id = ? AND m.user_id = ?
                    AND m.status = 'active'
                    AND memories_fts MATCH ?
                ORDER BY score
                LIMIT ?
            """, (device_id, user_id, or_query, top_k))
        else:
            # 搜索设备级记忆（user_id IS NULL）
            cursor = self.conn.execute(f"""
                SELECT
                    m.*,
                    bm25(memories_fts) as score
                FROM memories_fts fts
                JOIN memories m ON m.id = fts.id
                WHERE m.device_id = ? AND m.user_id IS NULL
                    AND m.status = 'active'
                    AND memories_fts MATCH ?
                ORDER BY score
                LIMIT ?
            """, (device_id, or_query, top_k))

        results = []
        for row in cursor.fetchall():
            memory = self._row_to_memory(row)
            score = row['score']
            results.append((memory, score))

        return results

    def get_intentions_in_range(
        self, device_id: str, user_id: Optional[str], start: datetime, end: datetime
    ) -> List[IntentionMemory]:
        """获取时间范围内的意图"""
        if user_id:
            cursor = self.conn.execute("""
                SELECT * FROM memories
                WHERE device_id = ? AND user_id = ?
                    AND type = ? AND status = ?
                    AND planned_time >= ? AND planned_time <= ?
                ORDER BY planned_time ASC
            """, (device_id, user_id, MemoryType.INTENTION.value, MemoryStatus.ACTIVE.value, start, end))
        else:
            # 查询设备级意图（user_id IS NULL）
            cursor = self.conn.execute("""
                SELECT * FROM memories
                WHERE device_id = ? AND user_id IS NULL
                    AND type = ? AND status = ?
                    AND planned_time >= ? AND planned_time <= ?
                ORDER BY planned_time ASC
            """, (device_id, MemoryType.INTENTION.value, MemoryStatus.ACTIVE.value, start, end))

        return [self._row_to_memory(row) for row in cursor.fetchall()]

    def _row_to_memory(self, row: sqlite3.Row) -> BaseMemory:
        """将数据库行转换为记忆对象"""
        memory_type = MemoryType(row['type'])

        common_data = {
            'id': row['id'],
            'device_id': row['device_id'],
            'user_id': row['user_id'],
            'type': memory_type,
            'content': row['content'],
            'original_language': row['original_language'] or 'zh',
            'created_at': datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            'updated_at': datetime.fromisoformat(row['updated_at']) if row['updated_at'] else datetime.now(),
            'status': MemoryStatus(row['status']) if row['status'] else MemoryStatus.ACTIVE,
            'importance': row['importance'] or 0.5,
            'access_count': row['access_count'] or 0,
            'last_accessed': datetime.fromisoformat(row['last_accessed']) if row['last_accessed'] else None,
            'related_ids': json.loads(row['related_ids']) if row['related_ids'] else [],
            'metadata': json.loads(row['metadata']) if row['metadata'] else {},
            'time_info': json.loads(row['time_info']) if row['time_info'] else None,
        }

        if memory_type == MemoryType.FACT:
            common_data['fact_type'] = row['fact_type']
            common_data['confidence'] = row['confidence'] or 1.0
            from memories.base import FactMemory
            return FactMemory(**common_data)

        elif memory_type == MemoryType.DANGER:
            from memories.base import DangerMemory
            common_data['danger_level'] = row['danger_level'] or "low"
            common_data['danger_category'] = row['danger_category'] or "other"
            common_data['severity_score'] = row['severity_score'] or 0.0
            common_data['already_notified'] = bool(row['already_notified'])
            return DangerMemory(**common_data)

        elif memory_type == MemoryType.INTENTION:
            common_data['intention_status'] = IntentionStatus(row['intention_status']) if row['intention_status'] else IntentionStatus.PLANNED
            common_data['planned_time'] = datetime.fromisoformat(row['planned_time']) if row['planned_time'] else None
            common_data['time_description'] = row['time_description']
            common_data['intention_type'] = row['intention_type']
            common_data['reminder_sent'] = bool(row['reminder_sent'])
            common_data['reminder_time'] = datetime.fromisoformat(row['reminder_time']) if row['reminder_time'] else None
            common_data['completed_at'] = datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None
            return IntentionMemory(**common_data)

        elif memory_type == MemoryType.PREFERENCE:
            from memories.base import PreferenceMemory
            common_data['preference_type'] = row['preference_type']
            common_data['preference_value'] = row['preference_value']
            return PreferenceMemory(**common_data)

        elif memory_type == MemoryType.PROFILE:
            from memories.base import UserProfile
            common_data['name'] = row['name']
            common_data['nickname'] = row['nickname']
            common_data['age'] = row['age']
            common_data['location'] = row['location']
            common_data['preferences'] = json.loads(row['preferences']) if row['preferences'] else {}
            common_data['relationships'] = json.loads(row['relationships']) if row['relationships'] else {}
            common_data['total_memories'] = row['total_memories'] or 0
            common_data['last_interaction'] = datetime.fromisoformat(row['last_interaction']) if row['last_interaction'] else None
            common_data['first_met'] = datetime.fromisoformat(row['first_met']) if row['first_met'] else None
            common_data['total_interaction_days'] = row['total_interaction_days'] or 0
            return UserProfile(**common_data)

        return BaseMemory(**common_data)

    def close(self):
        """关闭数据库连接"""
        self.conn.close()
