"""
不使用记忆，可以选择此模块
"""

from ..base import MemoryProviderBase, logger

TAG = __name__


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory=None):
        super().__init__(config)

    async def save_memory(self, msgs):
        logger.bind(tag=TAG).debug("nomem mode: No memory saving is performed.")
        return None

    async def query_memory(self, query: str) -> str:
        logger.bind(tag=TAG).debug("nomem mode: No memory query is performed.")
        return ""
