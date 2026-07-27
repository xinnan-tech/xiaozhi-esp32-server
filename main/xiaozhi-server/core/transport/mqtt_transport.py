import asyncio
import json
import time
from collections import deque
from typing import Any, AsyncGenerator, Dict, Optional
from .transport_interface import TransportInterface
from config.logger import setup_logging
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

logger = setup_logging()


class MQTTTransport(TransportInterface):
    """
    MQTT传输层实现：直接处理MQTT协议消息
    支持JSON消息和二进制音频数据传输
    """

    def __init__(self, mqtt_connection, udp_handler=None):
        """
        初始化MQTT传输层

        Args:
            mqtt_connection: MQTT连接对象，包含协议处理器
            udp_handler: UDP处理器，用于音频数据传输
        """
        self._mqtt_connection = mqtt_connection
        self._udp_handler = udp_handler
        queue_size = int(getattr(mqtt_connection, "message_queue_size", 128) or 128)
        self._audio_queue = deque(maxlen=max(1, queue_size))
        self._control_queue = deque(maxlen=max(32, min(queue_size, 128)))
        self._urgent_queue = deque(maxlen=32)
        self._arrival_sequence = 0
        self._message_event = asyncio.Event()
        self._closed = False

        # 设置MQTT连接的消息回调
        self._setup_message_handlers()

    def _setup_message_handlers(self):
        """设置消息处理回调"""
        # 设置MQTT消息接收回调
        self._mqtt_connection.set_message_callback(self._on_mqtt_message)

        # 设置UDP消息接收回调（如果有UDP处理器）
        if self._udp_handler:
            self._udp_handler.set_message_callback(self._on_udp_message)

    def _on_mqtt_message(self, topic: str, payload: str):
        """处理接收到的MQTT消息"""
        try:
            # 解析JSON消息
            message_data = json.loads(payload)
            message_data['_transport_type'] = 'mqtt'
            message_data['_topic'] = topic

            # Hello is a complete logical-session barrier. Discard all queued
            # work from the previous session before admitting the new Hello.
            if message_data.get("type") == "hello":
                self._audio_queue.clear()
                self._control_queue.clear()
                self._urgent_queue.clear()

            self._enqueue_message(message_data)

        except json.JSONDecodeError as e:
            logger.error(f"MQTT消息JSON解析失败: {e}, payload: {payload}")
        except Exception as e:
            logger.error(f"处理MQTT消息失败: {e}")

    def _on_udp_message(self, audio_data: bytes, timestamp: int):
        """处理接收到的UDP音频消息"""
        try:
            # 构造音频消息格式
            message_data = {
                'type': 'audio',
                'data': audio_data,
                'timestamp': timestamp,
                '_transport_type': 'udp'
            }

            self._enqueue_message(message_data)

        except Exception as e:
            logger.error(f"处理UDP音频消息失败: {e}")

    def _enqueue_message(self, message_data: Dict[str, Any]) -> None:
        self._arrival_sequence += 1
        queued_message = (self._arrival_sequence, message_data)
        if message_data.get("type") == "abort":
            self._urgent_queue.append(queued_message)
            self._message_event.set()
            return

        if message_data.get("type") == "audio":
            if len(self._audio_queue) >= self._audio_queue.maxlen:
                self._audio_queue.popleft()
                logger.warning("MQTT audio receive queue is full; evicted oldest frame")
            self._audio_queue.append(queued_message)
        else:
            if len(self._control_queue) >= self._control_queue.maxlen:
                boundary_types = {"hello", "goodbye"}
                evict_index = next(
                    (
                        index
                        for index, (_, queued) in enumerate(self._control_queue)
                        if queued.get("type") not in boundary_types
                    ),
                    None,
                )
                if evict_index is None:
                    if message_data.get("type") not in boundary_types:
                        logger.warning(
                            "MQTT control queue contains only session boundaries; "
                            "dropping non-boundary frame"
                        )
                        return
                    self._control_queue.popleft()
                else:
                    del self._control_queue[evict_index]
                logger.warning(
                    "MQTT control queue is full; evicted non-boundary control frame"
                )
            self._control_queue.append(queued_message)
        self._message_event.set()

    async def _next_message(self):
        while not self._closed:
            # Hello establishes the logical-session boundary. An Abort sent
            # immediately after the Hello reply must not overtake it and be
            # compared against the previous session.
            if (
                self._control_queue
                and self._control_queue[0][1].get("type") == "hello"
            ):
                return self._control_queue.popleft()[1]
            if self._urgent_queue:
                return self._urgent_queue.popleft()[1]
            if self._control_queue and self._audio_queue:
                queue = (
                    self._control_queue
                    if self._control_queue[0][0] < self._audio_queue[0][0]
                    else self._audio_queue
                )
                return queue.popleft()[1]
            if self._control_queue:
                return self._control_queue.popleft()[1]
            if self._audio_queue:
                return self._audio_queue.popleft()[1]

            self._message_event.clear()
            if self._urgent_queue or self._control_queue or self._audio_queue:
                continue
            await asyncio.wait_for(self._message_event.wait(), timeout=1.0)
        return None

    async def send(self, data: Any) -> None:
        """发送消息"""
        if self._closed:
            raise RuntimeError("Transport is closed")

        try:
            if isinstance(data, dict):
                # 根据消息类型选择传输方式
                if data.get('type') == 'audio' and self._udp_handler:
                    # 音频数据通过UDP发送
                    audio_data = data.get('data')
                    timestamp = data.get('timestamp', 0)
                    await self._udp_handler.send_audio(audio_data, timestamp)
                else:
                    # JSON消息通过MQTT发送
                    topic = data.get('_topic', self._mqtt_connection.reply_topic)
                    payload = json.dumps(data)
                    await self._mqtt_connection.send_message(topic, payload)

            elif isinstance(data, str):
                # 字符串消息通过MQTT发送
                await self._mqtt_connection.send_message(
                    self._mqtt_connection.reply_topic,
                    data
                )

            elif isinstance(data, bytes):
                # 二进制数据通过UDP发送（如果有UDP处理器）
                if self._udp_handler:
                    await self._udp_handler.send_audio(data, 0)
                else:
                    logger.warning("尝试发送二进制数据但没有UDP处理器")

            else:
                # 其他类型转换为字符串通过MQTT发送
                await self._mqtt_connection.send_message(
                    self._mqtt_connection.reply_topic,
                    str(data)
                )

        except Exception as e:
            logger.error(f"MQTT传输发送消息失败: {e}")
            raise

    async def send_json(self, message: Any) -> None:
        if isinstance(message, str):
            await self.send(message)
            return
        await self.send(dict(message))

    async def send_audio(self, audio: bytes, timestamp: int = 0) -> None:
        if not self._udp_handler:
            raise RuntimeError("UDP audio channel is not available")
        await self._udp_handler.send_audio(audio, timestamp)

    @property
    def requires_audio_tail_grace(self) -> bool:
        return True

    async def prepare_audio_channel(self, audio_params=None, version: int = 3) -> None:
        if not self._udp_handler:
            return
        if getattr(self._mqtt_connection, "udp_config", None) is None:
            await self._mqtt_connection.send_hello_reply(audio_params or {}, version)

    async def wait_audio_ready(self, timeout: float = 0) -> bool:
        if not self._udp_handler:
            return False
        deadline = time.monotonic() + max(timeout, 0)
        while getattr(self._udp_handler, "remote_address", None) is None:
            if time.monotonic() >= deadline:
                return False
            await asyncio.sleep(min(0.05, max(deadline - time.monotonic(), 0)))
        return True

    async def mark_business_ready(self) -> None:
        self._mqtt_connection.business_ready_event.set()
        schedule_recovery = getattr(
            self._mqtt_connection, "schedule_stale_session_recovery", None
        )
        if callable(schedule_recovery):
            schedule_recovery()

    async def mark_session_ready(self, session_id: str = None) -> None:
        self._mqtt_connection.mark_business_session_ready(session_id)

    async def end_session(self, session_id: str) -> None:
        await self._mqtt_connection.notify_device_idle(session_id)

    async def receive(self) -> AsyncGenerator[Any, None]:
        """异步消息流"""
        while not self._closed:
            try:
                # 等待消息，设置超时避免无限等待
                message = await self._next_message()
                if message is None:
                    break
                yield message

            except asyncio.TimeoutError:
                # 超时继续循环，检查连接状态
                if not self.is_connected:
                    break
                continue

            except Exception as e:
                logger.error(f"MQTT传输接收消息失败: {e}")
                break

    async def close(self) -> None:
        """关闭传输层"""
        if self._closed:
            return

        self._closed = True

        try:
            # 关闭MQTT连接
            if self._mqtt_connection:
                await self._mqtt_connection.close()

            # 关闭UDP处理器
            if self._udp_handler:
                await self._udp_handler.close()

        except Exception as e:
            logger.error(f"关闭MQTT传输层失败: {e}")
            raise RuntimeError("MQTT transport close failed")

    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        if self._closed:
            return False

        try:
            # 检查MQTT连接状态
            mqtt_connected = (
                self._mqtt_connection and
                self._mqtt_connection.is_connected()
            )

            return mqtt_connected

        except Exception as e:
            logger.error(f"检查MQTT连接状态失败: {e}")
            return False

    @property
    def device_id(self) -> Optional[str]:
        """获取设备ID"""
        return getattr(self._mqtt_connection, 'device_id', None)

    @property
    def client_id(self) -> Optional[str]:
        """获取客户端ID"""
        return getattr(self._mqtt_connection, 'client_id', None)

    @property
    def username(self) -> Optional[str]:
        """获取MQTT用户名"""
        return getattr(self._mqtt_connection, 'username', None)

    @property
    def password(self) -> Optional[str]:
        """获取MQTT密码"""
        return getattr(self._mqtt_connection, 'password', None)

    @property
    def session_id(self) -> Optional[str]:
        """获取会话ID"""
        return getattr(self._mqtt_connection, 'session_id', None)

    @property
    def transport_type(self) -> str:
        return "mqtt"

    @property
    def has_datagram_audio(self) -> bool:
        return self._udp_handler is not None

    @property
    def keeps_connection_between_sessions(self) -> bool:
        return True

    @property
    def is_protocol_authenticated(self) -> bool:
        return bool(getattr(self._mqtt_connection, "connect_accepted", False))

    @property
    def raw_connection(self):
        return self._mqtt_connection


class UDPAudioHandler:
    """
    UDP音频处理器：处理加密音频数据传输
    """

    def __init__(
        self,
        connection_id: int,
        udp_server,
        encryption_config: Dict[str, Any],
        allowed_remote_ip: Optional[str] = None,
    ):
        self.connection_id = connection_id
        self.udp_server = udp_server
        self.encryption_config = encryption_config
        self.allowed_remote_ip = allowed_remote_ip
        self.remote_address = None
        self.message_callback = None
        self.audio_interceptor = None
        self._closed = False
        self.local_sequence = 0
        self.remote_sequence = 0
        self.audio_sequence_start = None
        self.audio_start_time = None
        self.frame_ms = 60

    def set_message_callback(self, callback):
        """设置消息接收回调"""
        self.message_callback = callback

    def set_audio_interceptor(self, callback):
        self.audio_interceptor = callback

    def configure_encryption(self, udp_config: Dict[str, Any]):
        """设置UDP加密参数"""
        if not udp_config:
            return
        self.encryption_config = udp_config
        # A new Hello creates a new UDP session. Allow the first valid packet
        # from the MQTT peer to establish the new source tuple.
        self.remote_address = None
        self.reset_sequence()

    def reset_sequence(self):
        """重置UDP序列号（本地/远端）"""
        self.reset_local_sequence()
        self.reset_remote_sequence()

    def reset_local_sequence(self):
        """重置本地发送序列号"""
        self.local_sequence = 0

    def reset_remote_sequence(self):
        """重置远端接收序列号"""
        self.remote_sequence = 0
        self.audio_sequence_start = None
        self.audio_start_time = None

    async def send_audio(self, audio_data: bytes, timestamp: int):
        """发送音频数据"""
        if self._closed:
            raise RuntimeError("UDP audio handler is closed")
        if not self.remote_address:
            raise RuntimeError("UDP remote address is not ready")

        next_sequence = self.local_sequence + 1
        await self.udp_server.send_encrypted_audio(
            self.connection_id,
            audio_data,
            timestamp,
            next_sequence,
            self.remote_address,
            self.encryption_config
        )
        self.local_sequence = next_sequence

    def send_audio_nowait(self, audio_data: bytes, timestamp: int) -> bool:
        if self._closed or not self.remote_address:
            return False
        next_sequence = self.local_sequence + 1
        self.udp_server.send_encrypted_audio_nowait(
            self.connection_id,
            audio_data,
            timestamp,
            next_sequence,
            self.remote_address,
            self.encryption_config,
        )
        self.local_sequence = next_sequence
        return True

    def on_udp_message(self, header: bytes, encrypted_payload: bytes, payload_length: int,
                       timestamp: int, sequence: int, remote_addr):
        """处理接收到的UDP消息"""
        if self._closed:
            return

        if self.allowed_remote_ip and remote_addr[0] != self.allowed_remote_ip:
            logger.warning(
                "Rejected UDP packet from non-MQTT peer: {}, expected IP: {}",
                remote_addr,
                self.allowed_remote_ip,
            )
            return

        if self.remote_address is not None and remote_addr != self.remote_address:
            logger.warning(
                "Rejected UDP source rebind during active session: {}, bound: {}",
                remote_addr,
                self.remote_address,
            )
            return

        if self.audio_sequence_start is not None and sequence <= self.remote_sequence:
            return

        if sequence != self.remote_sequence + 1:
            logger.warning(
                "Received UDP packet with wrong sequence: {}, expected: {}",
                sequence,
                self.remote_sequence + 1
            )

        if len(encrypted_payload) != payload_length:
            logger.warning(
                "UDP payload length mismatch: {} != {}",
                len(encrypted_payload),
                payload_length,
            )
            return

        try:
            key = self.encryption_config.get('key') if self.encryption_config else None
            if key:
                cipher = Cipher(algorithms.AES(key), modes.CTR(header), backend=default_backend())
                decryptor = cipher.decryptor()
                payload = decryptor.update(encrypted_payload) + decryptor.finalize()
            else:
                payload = encrypted_payload
        except Exception as e:
            logger.error("UDP decrypt failed: {}", e)
            return

        if self.remote_address is None:
            self.remote_address = remote_addr
            self.audio_start_time = time.time()
            self.audio_sequence_start = sequence
            self.remote_sequence = sequence - 1

        if self.audio_sequence_start is None:
            self.audio_sequence_start = sequence

        self.remote_sequence = sequence

        normalized_timestamp = timestamp
        if timestamp == 0 and self.audio_sequence_start is not None:
            normalized_timestamp = (
                (sequence - self.audio_sequence_start) * self.frame_ms
            ) % (2 ** 32)

        if self.audio_interceptor and self.audio_interceptor(
            payload, normalized_timestamp
        ):
            return

        if self.message_callback:
            self.message_callback(payload, normalized_timestamp)

    async def close(self):
        """关闭UDP处理器"""
        self._closed = True
        self.message_callback = None
        self.audio_interceptor = None
        self.remote_address = None
