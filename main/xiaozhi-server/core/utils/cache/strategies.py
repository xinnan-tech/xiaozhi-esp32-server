"""
Cache strategy and data structure definitions
"""

import time
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass


class CacheStrategy(Enum):
    """Cache strategy enumeration"""
    TTL = "ttl"  # Time-based expiration
    LRU = "lru"  # Least Recently Used
    FIXED_SIZE = "fixed_size"  # Fixed size
    TTL_LRU = "ttl_lru"  # TTL + LRU hybrid strategy


@dataclass
class CacheEntry:
    """Cache entry data structure"""
    value: Any
    timestamp: float
    ttl: Optional[float] = None  # Time to live (seconds)
    access_count: int = 0
    last_access: float = None

    def __post_init__(self):
        if self.last_access is None:
            self.last_access = self.timestamp

    def is_expired(self) -> bool:
        """Check if expired"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def touch(self):
        """Update access time and count"""
        self.last_access = time.time()
        self.access_count += 1
