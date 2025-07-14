"""
缓存策略和数据结构定义
"""

import time
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass


class CacheStrategy(Enum):
    """缓存策略枚举"""

    TTL = "ttl"  # 基于时间过期
    LRU = "lru"  # 最近最少使用
    FIXED_SIZE = "fixed_size"  # 固定大小
    TTL_LRU = "ttl_lru"  # TTL + LRU混合策略


@dataclass
class CacheEntry:
    """缓存条目数据结构"""

    value: Any
    timestamp: float
    ttl: Optional[float] = None  # 生存时间（秒）
    access_count: int = 0
    last_access: float = None

    def __post_init__(self):
        if self.last_access is None:
            self.last_access = self.timestamp

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def touch(self):
        """更新访问时间和计数"""
        self.last_access = time.time()
        self.access_count += 1
