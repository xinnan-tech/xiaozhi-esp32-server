import asyncio
from typing import Dict, Any, Callable
from config.logger import setup_logging

logger = setup_logging()


# MQTT 固定头部的类型
class PacketType:
    CONNECT = 1
    CONNACK = 2
    PUBLISH = 3
    SUBSCRIBE = 8
    SUBACK = 9
    PINGREQ = 12
    PINGRESP = 13
    DISCONNECT = 14


class MQTTProtocol:
    """
    MQTT协议处理器：负责MQTT协议的解析和封装
    """

    def __init__(
        self,
        socket=None,
        reader=None,
        writer=None,
        max_payload_size=8192,
        event_queue_size=128,
        close_timeout=2,
    ):
        self.socket = socket
        self.reader = reader
        self.writer = writer
        self.buffer = b''
        self.event_handlers = {}
        self.is_connected = False
        self.keep_alive_interval = 0
        self.last_activity = 0
        self.max_payload_size = int(max_payload_size or 0)
        self.close_timeout = max(0.1, float(close_timeout or 2))
        self._closed = False
        self._application_queue = asyncio.Queue(
            maxsize=max(1, int(event_queue_size or 128))
        )

        # Application publishes stay ordered, while PINGREQ remains on the read
        # loop so a slow Hello/runtime refresh cannot starve MQTT keepalive.
        self._dispatch_task = asyncio.create_task(
            self._dispatch_application_messages()
        )
        self._processing_task = asyncio.create_task(self._process_messages())

    def on(self, event: str, handler: Callable):
        """注册事件处理器"""
        self.event_handlers[event] = handler

    def emit(self, event: str, *args, **kwargs):
        """触发事件"""
        handler = self.event_handlers.get(event)
        if handler:
            if asyncio.iscoroutinefunction(handler):
                asyncio.create_task(handler(*args, **kwargs))
            else:
                handler(*args, **kwargs)

    async def emit_async(self, event: str, *args, **kwargs):
        """Emit protocol events in packet order."""
        handler = self.event_handlers.get(event)
        if not handler:
            return None
        result = handler(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def _process_messages(self):
        """处理消息的主循环"""
        try:
            while not self._closed:
                # 从socket读取数据
                data = await self._read_socket()
                if not data:
                    break

                # 添加到缓冲区
                self.buffer += data

                # 处理缓冲区中的消息
                await self._process_buffer()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"MQTT消息处理循环出错: {e}")
            self.emit('error', e)
        finally:
            if not self._closed:
                if self._dispatch_task.done():
                    await self.emit_async('close')
                else:
                    # Preserve parsed QoS0 publishes before a normal peer EOF.
                    # The Hello/runtime barrier is separately time-bounded.
                    await self._application_queue.put({'type': 'peer_close'})

    async def _dispatch_application_messages(self):
        """Dispatch non-heartbeat packets sequentially outside the read loop."""
        try:
            while not self._closed:
                message = await self._application_queue.get()
                try:
                    await self._dispatch_application_message(message)
                finally:
                    self._application_queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"MQTT应用消息处理循环出错: {e}")
            self.emit('error', e)

    async def _dispatch_application_message(self, message: Dict[str, Any]):
        message_type = message.get('type')
        if message_type == 'publish':
            await self.emit_async('publish', message)
        elif message_type == 'disconnect':
            await self.emit_async('disconnect')
            self.is_connected = False
        elif message_type == 'peer_close':
            await self.emit_async('close')
        else:
            raise ValueError(f"不支持的MQTT应用消息类型: {message_type}")

    def _enqueue_application_message(self, message: Dict[str, Any]) -> None:
        try:
            self._application_queue.put_nowait(message)
        except asyncio.QueueFull as exc:
            raise ValueError("MQTT应用消息队列已满") from exc

    async def _read_socket(self) -> bytes:
        """从socket读取数据"""
        try:
            if self.reader is not None:
                return await self.reader.read(4096)
            # 使用asyncio的socket读取
            loop = asyncio.get_event_loop()
            data = await loop.sock_recv(self.socket, 4096)
            return data
        except Exception as e:
            logger.error(f"读取socket数据失败: {e}")
            return b''

    async def _process_buffer(self):
        """处理缓冲区中的消息"""
        while len(self.buffer) >= 2:  # 至少需要2字节开始解析
            try:
                # 解析消息
                message_length, message = self._parse_message()
                if message_length == 0:
                    break  # 消息不完整，等待更多数据

                # 从缓冲区移除已处理的消息
                self.buffer = self.buffer[message_length:]

                # 处理消息
                await self._handle_message(message)

            except Exception as e:
                logger.error(f"处理MQTT消息失败: {e}")
                self.emit('protocolError', e)
                break

    def _parse_message(self) -> tuple[int, Dict[str, Any]]:
        """解析MQTT消息"""
        if len(self.buffer) < 2:
            return 0, {}

        # 获取消息类型
        first_byte = self.buffer[0]
        packet_type = (first_byte >> 4)
        client_packet_types = {
            PacketType.CONNECT,
            PacketType.PUBLISH,
            PacketType.SUBSCRIBE,
            PacketType.PINGREQ,
            PacketType.DISCONNECT,
        }
        if packet_type not in client_packet_types:
            raise ValueError(f"不支持的客户端MQTT消息类型: {packet_type}")
        fixed_flags = first_byte & 0x0F
        expected_flags = {
            PacketType.CONNECT: 0,
            PacketType.SUBSCRIBE: 2,
            PacketType.PINGREQ: 0,
            PacketType.DISCONNECT: 0,
        }
        if (
            packet_type in expected_flags
            and fixed_flags != expected_flags[packet_type]
        ):
            raise ValueError(
                f"MQTT packet type {packet_type} has invalid fixed-header flags "
                f"0x{fixed_flags:x}"
            )
        if packet_type == PacketType.PUBLISH and ((first_byte >> 1) & 0x03) == 3:
            raise ValueError("MQTT PUBLISH QoS 3 is invalid")

        # 解析剩余长度
        remaining_length, bytes_read = self._decode_remaining_length()
        if remaining_length == -1:
            return 0, {}  # 长度解析失败，等待更多数据
        max_payload_size = getattr(self, "max_payload_size", 0)
        if max_payload_size > 0 and remaining_length > max_payload_size:
            raise ValueError(
                f"MQTT remaining length {remaining_length} exceeds limit {max_payload_size}"
            )

        # 计算完整消息长度
        total_length = 1 + bytes_read + remaining_length

        if len(self.buffer) < total_length:
            return 0, {}  # 消息不完整

        if (
            packet_type in (PacketType.PINGREQ, PacketType.DISCONNECT)
            and remaining_length != 0
        ):
            raise ValueError(
                f"MQTT packet type {packet_type} requires remaining length 0"
            )

        # 提取消息数据
        message_data = self.buffer[:total_length]

        # 根据消息类型解析
        if packet_type == PacketType.CONNECT:
            message = self._parse_connect(message_data)
        elif packet_type == PacketType.PUBLISH:
            message = self._parse_publish(message_data)
        elif packet_type == PacketType.SUBSCRIBE:
            message = self._parse_subscribe(message_data)
        elif packet_type == PacketType.PINGREQ:
            message = {'type': 'pingreq'}
        elif packet_type == PacketType.DISCONNECT:
            message = {'type': 'disconnect'}
        else:
            logger.warning(f"未处理的MQTT消息类型: {packet_type}")
            message = {'type': 'unknown', 'packet_type': packet_type}

        return total_length, message

    def _decode_remaining_length(self) -> tuple[int, int]:
        """解码剩余长度字段"""
        multiplier = 1
        value = 0
        bytes_read = 0

        while bytes_read < 4:
            if bytes_read + 1 >= len(self.buffer):
                return -1, 0
            digit = self.buffer[bytes_read + 1]
            bytes_read += 1

            value += (digit & 127) * multiplier
            multiplier *= 128

            if (digit & 128) == 0:
                return value, bytes_read
            if bytes_read == 4:
                raise ValueError("MQTT remaining length字段超过4字节")

        raise ValueError("MQTT remaining length字段无效")

    def _encode_remaining_length(self, length: int) -> bytes:
        """编码剩余长度字段"""
        result = bytearray()

        while True:
            digit = length % 128
            length = length // 128

            if length > 0:
                digit |= 0x80

            result.append(digit)

            if length == 0:
                break

        return bytes(result)

    def _parse_connect(self, message_data: bytes) -> Dict[str, Any]:
        """解析CONNECT消息"""
        try:
            # 跳过固定头部和剩余长度
            _, bytes_read = self._decode_remaining_length()
            pos = 1 + bytes_read

            def read_bytes(binary=False):
                nonlocal pos
                if pos + 2 > len(message_data):
                    raise ValueError("MQTT CONNECT字符串长度字段不完整")
                value_length = int.from_bytes(message_data[pos:pos + 2], 'big')
                pos += 2
                if pos + value_length > len(message_data):
                    raise ValueError("MQTT CONNECT字符串内容不完整")
                value = message_data[pos:pos + value_length]
                pos += value_length
                return value if binary else value.decode('utf-8')

            protocol = read_bytes()

            # 协议级别
            if pos + 4 > len(message_data):
                raise ValueError("MQTT CONNECT可变头部不完整")
            protocol_level = message_data[pos]
            pos += 1
            if protocol != 'MQTT' or protocol_level != 4:
                raise ValueError(
                    f"不支持的MQTT协议: {protocol}/{protocol_level}"
                )

            # 连接标志
            connect_flags = message_data[pos]
            if connect_flags & 0x01:
                raise ValueError("MQTT CONNECT保留标志必须为0")
            has_username = (connect_flags & 0x80) != 0
            has_password = (connect_flags & 0x40) != 0
            will_retain = (connect_flags & 0x20) != 0
            will_qos = (connect_flags >> 3) & 0x03
            has_will = (connect_flags & 0x04) != 0
            clean_session = (connect_flags & 0x02) != 0
            if has_password and not has_username:
                raise ValueError("MQTT CONNECT密码标志要求用户名标志")
            if will_qos == 3:
                raise ValueError("MQTT CONNECT Will QoS 3无效")
            if not has_will and (will_retain or will_qos):
                raise ValueError("MQTT CONNECT未启用Will但设置了Will标志")
            pos += 1

            # 保持连接时间
            keep_alive = int.from_bytes(message_data[pos:pos+2], 'big')
            pos += 2

            client_id = read_bytes()
            if not client_id and not clean_session:
                raise ValueError("MQTT CONNECT空clientId必须启用clean session")

            if has_will:
                read_bytes()  # Will topic
                read_bytes(binary=True)  # Will payload

            # 用户名（如果存在）
            username = ''
            if has_username:
                username = read_bytes()

            # 密码（如果存在）
            password = ''
            if has_password:
                password = read_bytes(binary=True).decode('utf-8')

            if pos != len(message_data):
                raise ValueError("MQTT CONNECT包含未解析的尾部数据")

            return {
                'type': 'connect',
                'protocol': protocol,
                'protocolLevel': protocol_level,
                'clientId': client_id,
                'keepAlive': keep_alive,
                'username': username,
                'password': password
            }

        except Exception as e:
            logger.error(f"解析CONNECT消息失败: {e}")
            raise

    def _parse_publish(self, message_data: bytes) -> Dict[str, Any]:
        """解析PUBLISH消息"""
        try:
            # 获取QoS等标志
            first_byte = message_data[0]
            qos = (first_byte & 0x06) >> 1
            dup = (first_byte & 0x08) != 0
            retain = (first_byte & 0x01) != 0

            # 跳过固定头部和剩余长度
            _, bytes_read = self._decode_remaining_length()
            pos = 1 + bytes_read

            # 主题长度
            if pos + 2 > len(message_data):
                raise ValueError("MQTT PUBLISH缺少主题长度")
            topic_length = int.from_bytes(message_data[pos:pos+2], 'big')
            pos += 2
            if topic_length == 0 or pos + topic_length > len(message_data):
                raise ValueError("MQTT PUBLISH主题为空或不完整")

            # 主题
            topic = message_data[pos:pos+topic_length].decode('utf-8')
            pos += topic_length
            if "\x00" in topic or "+" in topic or "#" in topic:
                raise ValueError("MQTT PUBLISH主题名称无效")

            # 消息ID（QoS > 0时存在）
            packet_id = None
            if qos > 0:
                if pos + 2 > len(message_data):
                    raise ValueError("MQTT PUBLISH缺少packetId")
                packet_id = int.from_bytes(message_data[pos:pos+2], 'big')
                pos += 2
                if packet_id == 0:
                    raise ValueError("MQTT PUBLISH packetId不能为0")

            # 有效载荷
            payload = message_data[pos:].decode('utf-8')

            return {
                'type': 'publish',
                'topic': topic,
                'payload': payload,
                'qos': qos,
                'dup': dup,
                'retain': retain,
                'packetId': packet_id
            }

        except Exception as e:
            logger.error(f"解析PUBLISH消息失败: {e}")
            raise

    def _parse_subscribe(self, message_data: bytes) -> Dict[str, Any]:
        """解析SUBSCRIBE消息"""
        try:
            # 跳过固定头部和剩余长度
            _, bytes_read = self._decode_remaining_length()
            pos = 1 + bytes_read

            # 消息ID
            if pos + 2 > len(message_data):
                raise ValueError("MQTT SUBSCRIBE缺少packetId")
            packet_id = int.from_bytes(message_data[pos:pos+2], 'big')
            pos += 2
            if packet_id == 0:
                raise ValueError("MQTT SUBSCRIBE packetId不能为0")

            # 主题长度
            if pos + 2 > len(message_data):
                raise ValueError("MQTT SUBSCRIBE缺少主题长度")
            topic_length = int.from_bytes(message_data[pos:pos+2], 'big')
            pos += 2
            if topic_length == 0 or pos + topic_length > len(message_data):
                raise ValueError("MQTT SUBSCRIBE主题为空或不完整")

            # 主题
            topic = message_data[pos:pos+topic_length].decode('utf-8')
            pos += topic_length
            if "\x00" in topic:
                raise ValueError("MQTT SUBSCRIBE主题过滤器无效")

            # QoS
            if pos >= len(message_data):
                raise ValueError("MQTT SUBSCRIBE缺少请求QoS")
            qos = message_data[pos]
            pos += 1
            if qos > 2:
                raise ValueError("MQTT SUBSCRIBE请求QoS无效")
            if pos != len(message_data):
                raise ValueError("MQTT SUBSCRIBE当前仅支持单个主题过滤器")

            return {
                'type': 'subscribe',
                'packetId': packet_id,
                'topic': topic,
                'qos': qos
            }

        except Exception as e:
            logger.error(f"解析SUBSCRIBE消息失败: {e}")
            raise

    async def _handle_message(self, message: Dict[str, Any]):
        """处理解析后的消息"""
        message_type = message.get('type')

        if message_type == 'connect':
            if self.is_connected:
                raise ValueError("MQTT连接只能发送一次CONNECT")
            self.keep_alive_interval = message.get('keepAlive', 0)
            accepted = await self.emit_async('connect', message)
            self.is_connected = accepted is not False
            if self.is_connected:
                self.emit('activity')
            return

        if not self.is_connected:
            raise ValueError("MQTT客户端必须先发送CONNECT")

        if message_type == 'publish':
            self.emit('activity')
            self._enqueue_application_message(message)
        elif message_type == 'subscribe':
            self.emit('activity')
            await self.emit_async('subscribe', message)
        elif message_type == 'pingreq':
            self.emit('activity')
            await self.send_pingresp()
        elif message_type == 'disconnect':
            self.emit('activity')
            self._enqueue_application_message(message)
        else:
            raise ValueError(f"不支持的MQTT消息类型: {message_type}")

    async def send_connack(self, return_code: int = 0, session_present: bool = False):
        """发送CONNACK消息"""
        packet = bytearray([
            PacketType.CONNACK << 4,  # 固定头部
            2,  # 剩余长度
            1 if session_present else 0,  # 连接确认标志
            return_code  # 返回码
        ])

        await self._send_packet(packet)

    async def send_publish(self, topic: str, payload: str, qos: int = 0,
                          dup: bool = False, retain: bool = False, packet_id: int = None):
        """发送PUBLISH消息"""
        # 构造固定头部
        first_byte = PacketType.PUBLISH << 4
        if dup:
            first_byte |= 0x08
        if qos > 0:
            first_byte |= (qos << 1)
        if retain:
            first_byte |= 0x01

        # 构造可变头部和载荷
        topic_bytes = topic.encode('utf-8')
        payload_bytes = payload.encode('utf-8')

        variable_header = bytearray()
        variable_header.extend(len(topic_bytes).to_bytes(2, 'big'))
        variable_header.extend(topic_bytes)

        if qos > 0 and packet_id is not None:
            variable_header.extend(packet_id.to_bytes(2, 'big'))

        # 计算剩余长度
        remaining_length = len(variable_header) + len(payload_bytes)
        remaining_length_bytes = self._encode_remaining_length(remaining_length)

        # 构造完整消息
        packet = bytearray([first_byte])
        packet.extend(remaining_length_bytes)
        packet.extend(variable_header)
        packet.extend(payload_bytes)

        await self._send_packet(packet)

    async def send_suback(self, packet_id: int, return_code: int = 0):
        """发送SUBACK消息"""
        packet = bytearray([
            PacketType.SUBACK << 4,  # 固定头部
            3,  # 剩余长度
            packet_id >> 8,  # 消息ID高字节
            packet_id & 0xFF,  # 消息ID低字节
            return_code  # 返回码
        ])

        await self._send_packet(packet)

    async def send_pingresp(self):
        """发送PINGRESP消息"""
        packet = bytearray([
            PacketType.PINGRESP << 4,  # 固定头部
            0  # 剩余长度
        ])

        await self._send_packet(packet)

    async def _send_packet(self, packet: bytearray):
        """发送数据包"""
        try:
            if self.writer is not None:
                self.writer.write(bytes(packet))
                await self.writer.drain()
            else:
                loop = asyncio.get_event_loop()
                await loop.sock_sendall(self.socket, bytes(packet))
        except Exception as e:
            logger.error(f"发送MQTT数据包失败: {e}")
            raise

    async def close(self):
        """关闭协议处理器"""
        self._closed = True
        current_task = asyncio.current_task()
        if (
            hasattr(self, '_processing_task')
            and self._processing_task is not current_task
            and not self._processing_task.done()
        ):
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        if (
            hasattr(self, '_dispatch_task')
            and self._dispatch_task is not current_task
            and not self._dispatch_task.done()
        ):
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass

        try:
            if self.writer is not None:
                self.writer.close()
                try:
                    await asyncio.wait_for(
                        self.writer.wait_closed(),
                        timeout=self.close_timeout,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "等待MQTT socket关闭超时，强制中止transport"
                    )
                    self.abort()
                except Exception:
                    pass
            elif self.socket:
                self.socket.close()
        except Exception as e:
            logger.error(f"关闭socket失败: {e}")

    def abort(self):
        """Force-close the underlying transport when graceful close stalls."""
        if self.writer is not None:
            transport = getattr(self.writer, "transport", None)
            if transport is not None:
                transport.abort()
                return
        if self.socket:
            self.socket.close()
