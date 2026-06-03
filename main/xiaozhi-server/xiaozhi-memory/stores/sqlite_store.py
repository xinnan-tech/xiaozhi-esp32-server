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
                last_interaction TIMESTAMP
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
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON memories(user_id)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON memories(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_planned_time ON memories(planned_time)")

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
        try:
            import jieba
            tokens = " ".join(jieba.lcut(memory.content))
        except ImportError:
            tokens = memory.content

        self.conn.execute("""
            INSERT INTO memories (
                id, user_id, type, content, original_language,
                created_at, updated_at, status, importance,
                tokens, related_ids, metadata, time_info,
                fact_type, confidence,
                intention_status, planned_time, time_description, intention_type,
                reminder_sent, reminder_time, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory.id,
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
        """获取用户所有活跃记忆"""
        cursor = self.conn.execute(
            "SELECT * FROM memories WHERE user_id = ? AND status = ? ORDER BY created_at DESC",
            (user_id, MemoryStatus.ACTIVE.value)
        )
        return [self._row_to_memory(row) for row in cursor.fetchall()]

    def search_fts(self, query: str, user_id: str, top_k: int = 10) -> List[tuple]:
        """
        使用FTS5 + BM25全文检索

        返回: [(memory, score), ...]
        """
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
        """, (user_id, query, top_k))

        results = []
        for row in cursor.fetchall():
            memory = self._row_to_memory(row)
            score = row['score']
            results.append((memory, score))

        return results

    def get_intentions_in_range(
        self, user_id: str, start: datetime, end: datetime
    ) -> List[IntentionMemory]:
        """获取时间范围内的意图"""
        cursor = self.conn.execute("""
            SELECT * FROM memories
            WHERE user_id = ?
                AND type = ?
                AND status = ?
                AND planned_time >= ?
                AND planned_time <= ?
            ORDER BY planned_time ASC
        """, (user_id, MemoryType.INTENTION.value, MemoryStatus.ACTIVE.value, start, end))

        return [self._row_to_memory(row) for row in cursor.fetchall()]

    def _row_to_memory(self, row: sqlite3.Row) -> BaseMemory:
        """将数据库行转换为记忆对象"""
        memory_type = MemoryType(row['type'])

        common_data = {
            'id': row['id'],
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
            return UserProfile(**common_data)

        return BaseMemory(**common_data)

    def close(self):
        """关闭数据库连接"""
        self.conn.close()
