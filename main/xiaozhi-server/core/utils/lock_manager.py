import asyncio
from typing import Dict
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class FileLockManager:
    _instance = None
    _locks: Dict[str, asyncio.Lock] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FileLockManager, cls).__new__(cls)
        return cls._instance

    @classmethod
    def get_lock(cls, file_path: str) -> asyncio.Lock:
        """获取指定文件的锁"""
        if file_path not in cls._locks:
            cls._locks[file_path] = asyncio.Lock()
        return cls._locks[file_path]

    @classmethod
    async def acquire_lock(cls, file_path: str):
        """获取锁"""
        lock = cls.get_lock(file_path)
        await lock.acquire()
        logger.bind(tag=TAG).debug(f"Acquired lock for {file_path}")

    @classmethod
    def release_lock(cls, file_path: str):
        """释放锁"""
        if file_path in cls._locks:
            try:
                cls._locks[file_path].release()
                logger.bind(tag=TAG).debug(f"Released lock for {file_path}")
            except RuntimeError as e:
                logger.bind(tag=TAG).warning(f"Failed to release lock for {file_path}: {e}")
