"""
Cache configuration management.
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .strategies import CacheStrategy


class CacheType(Enum):
    """Supported cache type definitions."""

    LOCATION = "location"
    WEATHER = "weather"
    INTENT = "intent"
    IP_INFO = "ip_info"
    CONFIG = "config"
    DEVICE_PROMPT = "device_prompt"
    VOICEPRINT_HEALTH = "voiceprint_health"  # Voiceprint health-check cache.
    AUDIO_DATA = "audio_data"  # Audio data cache.
    NEWS = "news"  # Latest-news brief cache (short TTL; news goes stale fast).


@dataclass
class CacheConfig:
    """Cache configuration."""

    strategy: CacheStrategy = CacheStrategy.TTL
    ttl: Optional[float] = 300  # Default: 5 minutes.
    max_size: Optional[int] = 1000  # Default: 1000 entries.
    cleanup_interval: float = 60  # Cleanup interval in seconds.

    @classmethod
    def for_type(cls, cache_type: CacheType) -> "CacheConfig":
        """Return the preset configuration for a cache type."""
        configs = {
            CacheType.LOCATION: cls(
                strategy=CacheStrategy.TTL, ttl=None, max_size=1000  # Manually invalidated.
            ),
            CacheType.IP_INFO: cls(
                strategy=CacheStrategy.TTL, ttl=86400, max_size=1000  # 24 hours.
            ),
            CacheType.WEATHER: cls(
                strategy=CacheStrategy.TTL, ttl=28800, max_size=1000  # 8 hours.
            ),
            CacheType.INTENT: cls(
                strategy=CacheStrategy.TTL_LRU, ttl=600, max_size=1000  # 10 minutes.
            ),
            CacheType.CONFIG: cls(
                strategy=CacheStrategy.FIXED_SIZE, ttl=None, max_size=20  # Manually invalidated.
            ),
            CacheType.DEVICE_PROMPT: cls(
                strategy=CacheStrategy.TTL, ttl=None, max_size=1000  # Manually invalidated.
            ),
            CacheType.VOICEPRINT_HEALTH: cls(
                strategy=CacheStrategy.TTL, ttl=600, max_size=100  # 10 minutes.
            ),
            CacheType.AUDIO_DATA: cls(
                strategy=CacheStrategy.TTL, ttl=600, max_size=100  # 10 minutes.
            ),
            CacheType.NEWS: cls(
                strategy=CacheStrategy.TTL, ttl=900, max_size=200  # 15 minutes.
            ),
        }
        return configs.get(cache_type, cls())
