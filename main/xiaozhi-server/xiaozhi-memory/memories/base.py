"""
基础记忆模型
"""
from datetime import datetime
from typing import Optional, List, Any
from enum import Enum
from pydantic import BaseModel, Field
import json


class MemoryType(str, Enum):
    """记忆类型"""
    FACT = "fact"
    INTENTION = "intention"
    PREFERENCE = "preference"
    PROFILE = "profile"
    DANGER = "danger"


class MemoryStatus(str, Enum):
    """记忆状态"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class IntentionStatus(str, Enum):
    """意图状态"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BaseMemory(BaseModel):
    """基础记忆类"""
    id: str
    device_id: str  # 设备ID（必填）
    user_id: Optional[str] = None  # 用户ID（可选，支持设备级共享记忆）
    type: MemoryType
    content: str
    original_language: str = "zh"  # 原始语言
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    status: MemoryStatus = MemoryStatus.ACTIVE
    importance: float = 0.5  # 重要性分数 0-1
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    # 向量检索相关（可选）
    embedding: Optional[List[float]] = None

    # FTS5检索相关
    tokens: Optional[str] = None  # 分词结果

    # 关联记忆
    related_ids: List[str] = Field(default_factory=list)

    # 元数据
    metadata: dict = Field(default_factory=dict)

    # 时间信息
    time_info: Optional[dict] = None


class FactMemory(BaseMemory):
    """事实记忆"""
    type: MemoryType = MemoryType.FACT
    fact_type: Optional[str] = None  # personal, professional, health, etc.
    confidence: float = 1.0


class IntentionMemory(BaseMemory):
    """意图记忆"""
    type: MemoryType = MemoryType.INTENTION
    intention_status: IntentionStatus = IntentionStatus.PLANNED
    planned_time: Optional[datetime] = None
    time_description: Optional[str] = None
    intention_type: Optional[str] = None  # meeting, travel, task, purchase, etc.
    reminder_sent: bool = False
    reminder_time: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PreferenceMemory(BaseMemory):
    """偏好记忆"""
    type: MemoryType = MemoryType.PREFERENCE
    preference_type: Optional[str] = None  # food, music, movie, etc.
    preference_value: Optional[str] = None  # like, dislike, neutral


class DangerMemory(BaseMemory):
    """危险行为记录"""
    type: MemoryType = MemoryType.DANGER
    danger_level: str = "low"  # low, medium, high, critical
    danger_category: Optional[str] = None  # physical, fire, electric, traffic, stranger, sharp_object, medicine, height, water, other
    severity_score: float = 0.0  # 0.0 ~ 1.0
    already_notified: bool = False  # 是否已推送通知


class UserProfile(BaseMemory):
    """用户画像"""
    type: MemoryType = MemoryType.PROFILE
    content: str = Field(default="用户画像")  # 默认内容
    name: Optional[str] = None
    nickname: Optional[str] = None
    age: Optional[int] = None
    location: Optional[str] = None
    preferences: dict = Field(default_factory=dict)
    relationships: dict = Field(default_factory=dict)
    total_memories: int = 0
    last_interaction: Optional[datetime] = None
    first_met: Optional[datetime] = None  # 第一次见面时间
    total_interaction_days: int = 0  # 累计互动天数
