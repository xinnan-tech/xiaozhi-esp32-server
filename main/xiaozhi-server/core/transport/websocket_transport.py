from typing import Any, AsyncGenerator
from .transport_interface import TransportInterface


class WebSocketTransport(TransportInterface):
    """
    WebSocket 传输实现：包装 websockets 库的协议对象，
    提供统一的 send/receive/close 接口。
    """

    def __init__(self, websocket):
        self._ws = websocket

    async def send(self, data: Any) -> None:
        if isinstance(data, (str, bytes)):
            await self._ws.send(data)
        else:
            await self._ws.send(str(data))

    async def receive(self) -> AsyncGenerator[Any, None]:
        async for message in self._ws:
            yield message

    async def close(self) -> None:
        try:
            if hasattr(self._ws, "closed") and not self._ws.closed:
                await self._ws.close()
            elif hasattr(self._ws, "state") and self._ws.state.name != "CLOSED":
                await self._ws.close()
            else:
                await self._ws.close()
        except Exception:
            raise RuntimeError("WebSocket close failed")

    @property
    def is_connected(self) -> bool:
        try:
            if hasattr(self._ws, "closed"):
                return not self._ws.closed
            if hasattr(self._ws, "state"):
                return getattr(self._ws.state, "name", "CLOSED") != "CLOSED"
        except Exception:
            raise RuntimeError("WebSocket connection check failed")
        return False


