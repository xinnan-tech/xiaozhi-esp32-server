from abc import ABC, abstractmethod
import json
from typing import Any, AsyncGenerator


class TransportInterface(ABC):
    """
    传输层抽象接口。
    """

    @abstractmethod
    async def send(self, data: Any) -> None:
        """发送一条消息。"""
        raise NotImplementedError

    async def send_json(self, message: Any) -> None:
        """Send a control message without exposing transport framing to callers."""
        payload = message if isinstance(message, str) else json.dumps(message)
        await self.send(payload)

    async def send_audio(self, audio: bytes, timestamp: int = 0) -> None:
        """Send one encoded audio frame over the transport's audio channel."""
        await self.send(audio)

    async def prepare_audio_channel(self, audio_params=None, version: int = 3) -> None:
        """Prepare transport-specific audio negotiation when required."""

    async def wait_audio_ready(self, timeout: float = 0) -> bool:
        """Wait until encoded audio can be delivered to the peer."""
        return True

    async def mark_business_ready(self) -> None:
        """Allow a transport handshake to proceed after runtime initialization."""

    async def mark_session_ready(self, session_id: str = None) -> None:
        """Release a logical-session handshake after its runtime is ready."""

    async def end_session(self, session_id: str) -> None:
        """Tell the device to return to Idle without closing the connection."""
        await self.send_json({"type": "goodbye", "session_id": session_id})

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

    @property
    def transport_type(self) -> str:
        """Stable transport identifier used by shared connection logic."""
        return "unknown"

    @property
    def has_datagram_audio(self) -> bool:
        """Whether audio is carried by a channel separate from control messages."""
        return False

    @property
    def requires_audio_tail_grace(self) -> bool:
        """Whether control can overtake the last audio frames of a turn."""
        return False

    @property
    def keeps_connection_between_sessions(self) -> bool:
        """Whether ending a conversation should leave the transport connected."""
        return False

    @property
    def is_protocol_authenticated(self) -> bool:
        """Whether the transport already authenticated the peer during handshake."""
        return False

    @property
    def raw_connection(self):
        """Underlying connection for temporary compatibility with legacy code."""
        return None

    @property
    def session_id(self):
        return None
