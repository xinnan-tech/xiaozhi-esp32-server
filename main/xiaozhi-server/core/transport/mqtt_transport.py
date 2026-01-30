import asyncio
import json
from typing import Any, AsyncGenerator, Dict, Optional
from .transport_interface import TransportInterface
from config.logger import setup_logging

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
        self._message_queue = asyncio.Queue()
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
            
            # 将消息放入队列
            asyncio.create_task(self._message_queue.put(message_data))
            
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
            
            # 将消息放入队列
            asyncio.create_task(self._message_queue.put(message_data))
            
        except Exception as e:
            logger.error(f"处理UDP音频消息失败: {e}")
    
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
    
    async def receive(self) -> AsyncGenerator[Any, None]:
        """异步消息流"""
        while not self._closed:
            try:
                # 等待消息，设置超时避免无限等待
                message = await asyncio.wait_for(
                    self._message_queue.get(), 
                    timeout=1.0
                )
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
    def session_id(self) -> Optional[str]:
        """获取会话ID"""
        return getattr(self._mqtt_connection, 'session_id', None)


class UDPAudioHandler:
    """
    UDP音频处理器：处理加密音频数据传输
    """
    
    def __init__(self, connection_id: int, udp_server, encryption_config: Dict[str, Any]):
        self.connection_id = connection_id
        self.udp_server = udp_server
        self.encryption_config = encryption_config
        self.remote_address = None
        self.message_callback = None
        self._closed = False
    
    def set_message_callback(self, callback):
        """设置消息接收回调"""
        self.message_callback = callback
    
    async def send_audio(self, audio_data: bytes, timestamp: int):
        """发送音频数据"""
        if self._closed or not self.remote_address:
            return
            
        try:
            # 使用UDP服务器发送加密音频数据
            await self.udp_server.send_encrypted_audio(
                self.connection_id,
                audio_data,
                timestamp,
                self.remote_address,
                self.encryption_config
            )
        except Exception as e:
            logger.error(f"发送UDP音频数据失败: {e}")
    
    def on_udp_message(self, audio_data: bytes, timestamp: int, remote_addr):
        """处理接收到的UDP消息"""
        if self._closed:
            return
            
        # 记录远程地址
        if not self.remote_address:
            self.remote_address = remote_addr
        
        # 调用回调函数
        if self.message_callback:
            self.message_callback(audio_data, timestamp)
    
    async def close(self):
        """关闭UDP处理器"""
        self._closed = True
        self.message_callback = None
        self.remote_address = None

