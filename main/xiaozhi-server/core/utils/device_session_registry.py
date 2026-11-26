import asyncio
from typing import Any, Dict, Optional

TAG = __name__


class DeviceSessionRegistry:
    """(device-id → 活跃 ConnectionHandler) 注册表。

    同一台设备重连时，新连接必须先让旧会话收敛：否则两条 ConnectionHandler
    同时存在，会出现回复串台、丢回复，旧会话的 ASR/LLM/TTS 继续占用下游连接，
    直到 120s+60s 的静默超时才被回收（#3526）。
    """

    def __init__(self) -> None:
        self._handlers: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def bind(self, device_id: Optional[str], handler: Any) -> Optional[Any]:
        """登记新会话并返回被顶替的旧会话（没有则返回 None）。"""
        if not device_id:
            return None
        async with self._lock:
            old = self._handlers.get(device_id)
            if old is handler:
                return None
            self._handlers[device_id] = handler
            return old

    async def release(self, device_id: Optional[str], handler: Any) -> bool:
        """会话结束时注销；只有自己仍是登记对象时才移除，避免误删新会话。"""
        if not device_id:
            return False
        async with self._lock:
            if self._handlers.get(device_id) is handler:
                self._handlers.pop(device_id, None)
                return True
            return False

    def get(self, device_id: Optional[str]) -> Optional[Any]:
        if not device_id:
            return None
        return self._handlers.get(device_id)

    def active_count(self) -> int:
        return len(self._handlers)
