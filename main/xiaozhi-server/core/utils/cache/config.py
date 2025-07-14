"""
缓存配置管理
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .strategies import CacheStrategy


class CacheType(Enum):
    """缓存类型枚举"""

    LOCATION = "location"
    WEATHER = "weather"
    LUNAR = "lunar"
    INTENT = "intent"
    IP_INFO = "ip_info"
    CONFIG = "config"
    DEVICE_PROMPT = "device_prompt"


@dataclass
class CacheConfig:
    """缓存配置类"""

    strategy: CacheStrategy = CacheStrategy.TTL
    ttl: Optional[float] = 300  # 默认5分钟
    max_size: Optional[int] = 1000  # 默认最大1000条
    cleanup_interval: float = 60  # 清理间隔（秒）

    @classmethod
    def for_type(cls, cache_type: CacheType) -> "CacheConfig":
        """根据缓存类型返回预设配置"""
        configs = {
            CacheType.LOCATION: cls(
                strategy=CacheStrategy.TTL, ttl=None, max_size=1000  # 手动失效
            ),
            CacheType.IP_INFO: cls(
                strategy=CacheStrategy.TTL, ttl=86400, max_size=1000  # 24小时
            ),
            CacheType.WEATHER: cls(
                strategy=CacheStrategy.TTL, ttl=28800, max_size=1000  # 8小时
            ),
            CacheType.LUNAR: cls(
                strategy=CacheStrategy.TTL, ttl=2592000, max_size=365  # 30天过期
            ),
            CacheType.INTENT: cls(
                strategy=CacheStrategy.TTL_LRU, ttl=600, max_size=1000  # 10分钟
            ),
            CacheType.CONFIG: cls(
                strategy=CacheStrategy.FIXED_SIZE, ttl=None, max_size=20  # 手动失效
            ),
            CacheType.DEVICE_PROMPT: cls(
                strategy=CacheStrategy.TTL, ttl=None, max_size=1000  # 手动失效
            ),
        }
        return configs.get(cache_type, cls())
