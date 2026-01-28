from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator


class TransportInterface(ABC):
    """
    传输层抽象接口。
    """

    @abstractmethod
    async def send(self, data: Any) -> None:
        """发送一条消息。"""
        raise NotImplementedError

    @abstractmethod
    async def receive(self) -> AsyncGenerator[Any, None]:
        """异步消息流。"""
        yield  # pragma: no cover

    @abstractmethod
    async def close(self) -> None:
        """关闭底层连接。"""
        raise NotImplementedError

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """连接是否存活。"""
        raise NotImplementedError


