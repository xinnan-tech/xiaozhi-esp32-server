import struct
import time
from typing import Any, AsyncGenerator
from .transport_interface import TransportInterface


class WebSocketTransport(TransportInterface):
    """
    WebSocket 传输实现：包装 websockets 库的协议对象，
    提供统一的 send/receive/close 接口。
    """

    def __init__(
        self,
        websocket,
        from_mqtt_gateway: bool = False,
        protocol_version: int = 1,
    ):
        self._ws = websocket
        self._from_mqtt_gateway = from_mqtt_gateway
        self._protocol_version = protocol_version if protocol_version in (1, 2, 3) else 1
        self._gateway_sequence = 0

    async def send(self, data: Any) -> None:
        if isinstance(data, bytes):
            await self.send_audio(data)
            return

        if isinstance(data, (str, bytes)):
            await self._ws.send(data)
        else:
            await self._ws.send(str(data))

    async def send_audio(self, audio: bytes, timestamp: int = 0) -> None:
        if self._from_mqtt_gateway:
            await self._ws.send(self._frame_gateway_audio(audio, timestamp))
            return
        await self._ws.send(self._frame_websocket_audio(audio, timestamp))

    def _frame_websocket_audio(self, audio: bytes, timestamp: int = 0) -> bytes:
        if self._protocol_version == 2:
            return struct.pack("!HHIII", 2, 0, 0, timestamp, len(audio)) + audio
        if self._protocol_version == 3:
            return struct.pack("!BBH", 0, 0, len(audio)) + audio
        return audio

    def _parse_websocket_audio(self, message: bytes):
        if self._protocol_version == 2:
            if len(message) < 16:
                return None
            version, message_type, _, timestamp, audio_length = struct.unpack(
                "!HHIII", message[:16]
            )
            if (
                version != 2
                or message_type != 0
                or audio_length <= 0
                or len(message) != 16 + audio_length
            ):
                return None
            return {
                "type": "audio",
                "data": message[16:],
                "timestamp": timestamp,
                "_transport_type": "websocket",
            }
        if self._protocol_version == 3:
            if len(message) < 4:
                return None
            message_type, _, audio_length = struct.unpack("!BBH", message[:4])
            if (
                message_type != 0
                or audio_length <= 0
                or len(message) != 4 + audio_length
            ):
                return None
            return {
                "type": "audio",
                "data": message[4:],
                "timestamp": 0,
                "_transport_type": "websocket",
            }
        return message

    def _frame_gateway_audio(self, audio: bytes, timestamp: int = 0) -> bytes:
        self._gateway_sequence += 1
        if timestamp <= 0:
            timestamp = int(time.time() * 1000) % (2 ** 32)
        header = bytearray(16)
        header[0] = 1
        header[2:4] = len(audio).to_bytes(2, "big")
        header[4:8] = self._gateway_sequence.to_bytes(4, "big")
        header[8:12] = timestamp.to_bytes(4, "big")
        header[12:16] = len(audio).to_bytes(4, "big")
        return bytes(header) + audio

    async def receive(self) -> AsyncGenerator[Any, None]:
        async for message in self._ws:
            if self._from_mqtt_gateway and isinstance(message, bytes):
                if len(message) < 16:
                    continue
                if message[:8] != b"\x00" * 8:
                    continue
                timestamp = int.from_bytes(message[8:12], "big")
                audio_length = int.from_bytes(message[12:16], "big")
                if audio_length <= 0 or len(message) != 16 + audio_length:
                    continue
                message = {
                    "type": "audio",
                    "data": message[16:],
                    "timestamp": timestamp,
                    "_transport_type": "gateway",
                }
            elif isinstance(message, bytes):
                message = self._parse_websocket_audio(message)
                if message is None:
                    continue
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

    @property
    def transport_type(self) -> str:
        return "gateway" if self._from_mqtt_gateway else "websocket"

    @property
    def requires_audio_tail_grace(self) -> bool:
        # The gateway receives MQTT control and UDP audio independently before
        # serializing both streams onto this WebSocket.
        return self._from_mqtt_gateway

    @property
    def raw_connection(self):
        return self._ws
