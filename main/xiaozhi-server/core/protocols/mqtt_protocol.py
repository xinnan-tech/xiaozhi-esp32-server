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
    
    def __init__(self, socket):
        self.socket = socket
        self.buffer = b''
        self.event_handlers = {}
        self.is_connected = False
        self.keep_alive_interval = 0
        self.last_activity = 0
        
        # 启动消息处理任务
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
    
    async def _process_messages(self):
        """处理消息的主循环"""
        try:
            while True:
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
            self.emit('close')
    
    async def _read_socket(self) -> bytes:
        """从socket读取数据"""
        try:
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
        
        # 解析剩余长度
        remaining_length, bytes_read = self._decode_remaining_length()
        if remaining_length == -1:
            return 0, {}  # 长度解析失败，等待更多数据
        
        # 计算完整消息长度
        total_length = 1 + bytes_read + remaining_length
        
        if len(self.buffer) < total_length:
            return 0, {}  # 消息不完整
        
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
        
        while bytes_read < 4 and bytes_read + 1 < len(self.buffer):
            digit = self.buffer[bytes_read + 1]
            bytes_read += 1
            
            value += (digit & 127) * multiplier
            multiplier *= 128
            
            if (digit & 128) == 0:
                break
        else:
            if bytes_read >= 4:
                return -1, 0  # 长度字段过长
            return -1, 0  # 数据不完整
        
        return value, bytes_read
    
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
            
            # 协议名长度
            protocol_length = int.from_bytes(message_data[pos:pos+2], 'big')
            pos += 2
            
            # 协议名
            protocol = message_data[pos:pos+protocol_length].decode('utf-8')
            pos += protocol_length
            
            # 协议级别
            protocol_level = message_data[pos]
            pos += 1
            
            # 连接标志
            connect_flags = message_data[pos]
            has_username = (connect_flags & 0x80) != 0
            has_password = (connect_flags & 0x40) != 0
            pos += 1
            
            # 保持连接时间
            keep_alive = int.from_bytes(message_data[pos:pos+2], 'big')
            pos += 2
            
            # 客户端ID
            client_id_length = int.from_bytes(message_data[pos:pos+2], 'big')
            pos += 2
            client_id = message_data[pos:pos+client_id_length].decode('utf-8')
            pos += client_id_length
            
            # 用户名（如果存在）
            username = ''
            if has_username:
                username_length = int.from_bytes(message_data[pos:pos+2], 'big')
                pos += 2
                username = message_data[pos:pos+username_length].decode('utf-8')
                pos += username_length
            
            # 密码（如果存在）
            password = ''
            if has_password:
                password_length = int.from_bytes(message_data[pos:pos+2], 'big')
                pos += 2
                password = message_data[pos:pos+password_length].decode('utf-8')
                pos += password_length
            
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
            topic_length = int.from_bytes(message_data[pos:pos+2], 'big')
            pos += 2
            
            # 主题
            topic = message_data[pos:pos+topic_length].decode('utf-8')
            pos += topic_length
            
            # 消息ID（QoS > 0时存在）
            packet_id = None
            if qos > 0:
                packet_id = int.from_bytes(message_data[pos:pos+2], 'big')
                pos += 2
            
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
            packet_id = int.from_bytes(message_data[pos:pos+2], 'big')
            pos += 2
            
            # 主题长度
            topic_length = int.from_bytes(message_data[pos:pos+2], 'big')
            pos += 2
            
            # 主题
            topic = message_data[pos:pos+topic_length].decode('utf-8')
            pos += topic_length
            
            # QoS
            qos = message_data[pos]
            
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
            self.keep_alive_interval = message.get('keepAlive', 0)
            self.is_connected = True
            self.emit('connect', message)
        elif message_type == 'publish':
            self.emit('publish', message)
        elif message_type == 'subscribe':
            self.emit('subscribe', message)
        elif message_type == 'pingreq':
            await self.send_pingresp()
        elif message_type == 'disconnect':
            self.emit('disconnect')
        else:
            logger.warning(f"未处理的消息类型: {message_type}")
    
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
            loop = asyncio.get_event_loop()
            await loop.sock_sendall(self.socket, bytes(packet))
        except Exception as e:
            logger.error(f"发送MQTT数据包失败: {e}")
            raise
    
    async def close(self):
        """关闭协议处理器"""
        if hasattr(self, '_processing_task') and not self._processing_task.done():
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        try:
            self.socket.close()
        except Exception as e:
            logger.error(f"关闭socket失败: {e}")

