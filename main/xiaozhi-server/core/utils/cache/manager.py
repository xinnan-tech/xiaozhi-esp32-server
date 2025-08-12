"""
全局缓存管理器
"""

import time
import threading
from typing import Any, Optional, Dict
from collections import OrderedDict
from .strategies import CacheStrategy, CacheEntry
from .config import CacheConfig, CacheType


class GlobalCacheManager:
    """全局缓存管理器"""

    def __init__(self):
        self._logger = None
        self._caches: Dict[str, Dict[str, CacheEntry]] = {}
        self._configs: Dict[str, CacheConfig] = {}
        self._locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()
        self._last_cleanup = time.time()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "cleanups": 0}

    @property
    def logger(self):
        """延迟初始化 logger 以避免循环导入"""
        if self._logger is None:
            from config.logger import setup_logging

            self._logger = setup_logging()
        return self._logger

    def _get_cache_name(self, cache_type: CacheType, namespace: str = "") -> str:
        """生成缓存名称"""
        if namespace:
            return f"{cache_type.value}:{namespace}"
        return cache_type.value

    def _get_or_create_cache(
        self, cache_name: str, config: CacheConfig
    ) -> Dict[str, CacheEntry]:
        """获取或创建缓存空间"""
        with self._global_lock:
            if cache_name not in self._caches:
                self._caches[cache_name] = (
                    OrderedDict()
                    if config.strategy in [CacheStrategy.LRU, CacheStrategy.TTL_LRU]
                    else {}
                )
                self._configs[cache_name] = config
                self._locks[cache_name] = threading.RLock()
            return self._caches[cache_name]

    def set(
        self,
        cache_type: CacheType,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        namespace: str = "",
    ) -> None:
        """设置缓存值"""
        cache_name = self._get_cache_name(cache_type, namespace)
        config = self._configs.get(cache_name) or CacheConfig.for_type(cache_type)
        cache = self._get_or_create_cache(cache_name, config)

        # 使用配置的TTL或传入的TTL
        effective_ttl = ttl if ttl is not None else config.ttl

        with self._locks[cache_name]:
            # 创建缓存条目
            entry = CacheEntry(value=value, timestamp=time.time(), ttl=effective_ttl)

            # 处理不同策略
            if config.strategy in [CacheStrategy.LRU, CacheStrategy.TTL_LRU]:
                # LRU策略：如果已存在则移动到末尾
                if key in cache:
                    del cache[key]
                cache[key] = entry

                # 检查大小限制
                if config.max_size and len(cache) > config.max_size:
                    # 移除最旧的条目
                    oldest_key = next(iter(cache))
                    del cache[oldest_key]
                    self._stats["evictions"] += 1

            else:
                cache[key] = entry

                # 检查大小限制
                if config.max_size and len(cache) > config.max_size:
                    # 简单策略：随机移除一个条目
                    victim_key = next(iter(cache))
                    del cache[victim_key]
                    self._stats["evictions"] += 1

        # 定期清理过期条目
        self._maybe_cleanup(cache_name)

    def get(
        self, cache_type: CacheType, key: str, namespace: str = ""
    ) -> Optional[Any]:
        """获取缓存值"""
        cache_name = self._get_cache_name(cache_type, namespace)

        if cache_name not in self._caches:
            self._stats["misses"] += 1
            return None

        cache = self._caches[cache_name]
        config = self._configs[cache_name]

        with self._locks[cache_name]:
            if key not in cache:
                self._stats["misses"] += 1
                return None

            entry = cache[key]

            # 检查过期
            if entry.is_expired():
                del cache[key]
                self._stats["misses"] += 1
                return None

            # 更新访问信息
            entry.touch()

            # LRU策略：移动到末尾
            if config.strategy in [CacheStrategy.LRU, CacheStrategy.TTL_LRU]:
                del cache[key]
                cache[key] = entry

            self._stats["hits"] += 1
            return entry.value

    def delete(self, cache_type: CacheType, key: str, namespace: str = "") -> bool:
        """删除缓存条目"""
        cache_name = self._get_cache_name(cache_type, namespace)

        if cache_name not in self._caches:
            return False

        cache = self._caches[cache_name]

        with self._locks[cache_name]:
            if key in cache:
                del cache[key]
                return True
            return False

    def clear(self, cache_type: CacheType, namespace: str = "") -> None:
        """清空指定缓存"""
        cache_name = self._get_cache_name(cache_type, namespace)

        if cache_name not in self._caches:
            return

        with self._locks[cache_name]:
            self._caches[cache_name].clear()

    def invalidate_pattern(
        self, cache_type: CacheType, pattern: str, namespace: str = ""
    ) -> int:
        """按模式失效缓存条目"""
        cache_name = self._get_cache_name(cache_type, namespace)

        if cache_name not in self._caches:
            return 0

        cache = self._caches[cache_name]
        deleted_count = 0

        with self._locks[cache_name]:
            keys_to_delete = [key for key in cache.keys() if pattern in key]
            for key in keys_to_delete:
                del cache[key]
                deleted_count += 1

        return deleted_count

    def _cleanup_expired(self, cache_name: str) -> int:
        """清理过期条目"""
        if cache_name not in self._caches:
            return 0

        cache = self._caches[cache_name]
        deleted_count = 0

        with self._locks[cache_name]:
            expired_keys = [key for key, entry in cache.items() if entry.is_expired()]
            for key in expired_keys:
                del cache[key]
                deleted_count += 1

        return deleted_count

    def _maybe_cleanup(self, cache_name: str):
        """定期清理检查"""
        config = self._configs.get(cache_name)
        if not config:
            return

        now = time.time()
        if now - self._last_cleanup > config.cleanup_interval:
            self._last_cleanup = now
            deleted = self._cleanup_expired(cache_name)
            if deleted > 0:
                self._stats["cleanups"] += 1
                self.logger.debug(f"清理缓存 {cache_name}: 删除 {deleted} 个过期条目")


# 创建全局缓存管理器实例
cache_manager = GlobalCacheManager()