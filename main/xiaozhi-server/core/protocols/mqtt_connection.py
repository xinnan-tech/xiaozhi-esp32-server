import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, Callable
from config.logger import setup_logging

logger = setup_logging()


class MQTTConnection:
    """
    MQTT连接处理类：管理单个MQTT客户端连接
    处理MQTT协议消息和会话管理
    """
    
    def __init__(self, socket, connection_id: int, mqtt_server):
        self.socket = socket
        self.connection_id = connection_id
        self.mqtt_server = mqtt_server
        
        # 连接信息
        self.client_id = None
        self.device_id = None
        self.username = None
        self.password = None
        self.session_id = None
        
        # 协议状态
        self.is_connected_flag = False
        self.keep_alive_interval = 0
        self.last_activity = time.time()
        
        # 消息处理
        self.message_callback = None
        self.reply_topic = None
        
        # UDP相关
        self.udp_config = None
        
        # 任务管理
        self.keep_alive_task = None
        self._closed = False
        
        # 创建MQTT协议处理器
        from core.protocols.mqtt_protocol import MQTTProtocol
        self.protocol = MQTTProtocol(socket)
        self._setup_protocol_handlers()
    
    def _setup_protocol_handlers(self):
        """设置协议事件处理"""
        self.protocol.on('connect', self._handle_connect)
        self.protocol.on('publish', self._handle_publish)
        self.protocol.on('subscribe', self._handle_subscribe)
        self.protocol.on('disconnect', self._handle_disconnect)
        self.protocol.on('close', self._handle_close)
        self.protocol.on('error', self._handle_error)
    
    async def _handle_connect(self, connect_data: Dict[str, Any]):
        """处理CONNECT消息"""
        try:
            self.client_id = connect_data['clientId']
            self.username = connect_data.get('username')
            self.password = connect_data.get('password')
            self.keep_alive_interval = connect_data.get('keepAlive', 0) * 1000  # 转换为毫秒
            
            logger.info(f"MQTT客户端连接: {self.client_id}")
            
            # 解析客户端ID获取设备信息
            if not self._parse_client_id():
                await self.protocol.send_connack(1)  # 连接被拒绝
                await self.close()
                return
            
            # 生成会话ID
            self.session_id = str(uuid.uuid4())
            
            # 设置回复主题
            self.reply_topic = f"devices/p2p/{self.device_id.replace(':', '_')}"
            
            # 发送连接确认
            await self.protocol.send_connack(0)  # 连接接受
            self.is_connected_flag = True
            
            # 启动心跳检查
            if self.keep_alive_interval > 0:
                self.keep_alive_task = asyncio.create_task(self._keep_alive_check())
            
            # 通知服务器新连接
            await self.mqtt_server.on_client_connected(self)
            
        except Exception as e:
            logger.error(f"处理CONNECT消息失败: {e}")
            await self.close()
    
    def _parse_client_id(self) -> bool:
        """解析客户端ID获取设备信息"""
        try:
            # 支持格式: GID_test@@@mac_address@@@uuid 或 GID_test@@@mac_address
            parts = self.client_id.split('@@@')
            
            if len(parts) >= 2:
                self.group_id = parts[0]
                # 将下划线替换为冒号格式的MAC地址
                self.device_id = parts[1].replace('_', ':')
                
                if len(parts) >= 3:
                    self.uuid = parts[2]
                
                return True
            else:
                logger.error(f"无效的客户端ID格式: {self.client_id}")
                return False
                
        except Exception as e:
            logger.error(f"解析客户端ID失败: {e}")
            return False
    
    async def _handle_publish(self, publish_data: Dict[str, Any]):
        """处理PUBLISH消息"""
        try:
            topic = publish_data['topic']
            payload = publish_data['payload']
            
            logger.debug(f"收到MQTT发布消息: topic={topic}, payload={payload}")
            
            # 更新活动时间
            self.last_activity = time.time()
            
            # 解析JSON消息
            try:
                message_data = json.loads(payload)
                
                # 处理不同类型的消息
                if message_data.get('type') == 'hello':
                    await self._handle_hello_message(message_data)
                else:
                    # 其他消息通过回调处理
                    if self.message_callback:
                        self.message_callback(topic, payload)
                        
            except json.JSONDecodeError:
                logger.error(f"MQTT消息JSON解析失败: {payload}")
                
        except Exception as e:
            logger.error(f"处理PUBLISH消息失败: {e}")
    
    async def _handle_hello_message(self, message_data: Dict[str, Any]):
        """处理hello消息，初始化UDP配置"""
        try:
            # 生成UDP加密配置
            import os
            
            self.udp_config = {
                'key': os.urandom(16),
                'encryption': 'aes-128-ctr',
                'server': self.mqtt_server.public_ip,
                'port': self.mqtt_server.udp_port
            }
            
            # 构造hello回复
            hello_reply = {
                'type': 'hello',
                'version': message_data.get('version', 3),
                'session_id': self.session_id,
                'transport': 'udp',
                'udp': {
                    'server': self.udp_config['server'],
                    'port': self.udp_config['port'],
                    'encryption': self.udp_config['encryption'],
                    'key': self.udp_config['key'].hex(),
                    'nonce': '00' * 16  # 临时nonce
                },
                'audio_params': message_data.get('audio_params', {})
            }
            
            # 发送回复
            await self.send_message(self.reply_topic, json.dumps(hello_reply))
            
            logger.info(f"MQTT Hello消息处理完成: {self.client_id}")
            
        except Exception as e:
            logger.error(f"处理hello消息失败: {e}")
    
    async def _handle_subscribe(self, subscribe_data: Dict[str, Any]):
        """处理SUBSCRIBE消息"""
        try:
            topic = subscribe_data['topic']
            packet_id = subscribe_data['packetId']
            
            logger.debug(f"客户端订阅主题: {topic}")
            
            # 发送订阅确认
            await self.protocol.send_suback(packet_id, 0)
            
        except Exception as e:
            logger.error(f"处理SUBSCRIBE消息失败: {e}")
    
    async def _handle_disconnect(self):
        """处理DISCONNECT消息"""
        logger.info(f"客户端主动断开连接: {self.client_id}")
        await self.close()
    
    async def _handle_close(self):
        """处理连接关闭"""
        logger.info(f"MQTT连接关闭: {self.client_id}")
        await self.close()
    
    async def _handle_error(self, error):
        """处理连接错误"""
        logger.error(f"MQTT连接错误: {self.client_id}, error: {error}")
        await self.close()
    
    async def _keep_alive_check(self):
        """心跳检查任务"""
        try:
            while self.is_connected_flag and not self._closed:
                await asyncio.sleep(self.keep_alive_interval / 1000 / 2)  # 检查间隔为心跳间隔的一半
                
                current_time = time.time()
                if current_time - self.last_activity > self.keep_alive_interval / 1000 * 1.5:
                    logger.info(f"MQTT客户端心跳超时: {self.client_id}")
                    await self.close()
                    break
                    
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"心跳检查任务出错: {e}")
    
    def set_message_callback(self, callback: Callable[[str, str], None]):
        """设置消息接收回调"""
        self.message_callback = callback
    
    async def send_message(self, topic: str, payload: str):
        """发送MQTT消息"""
        if self._closed or not self.is_connected_flag:
            return
            
        try:
            await self.protocol.send_publish(topic, payload, qos=0)
            logger.debug(f"发送MQTT消息: topic={topic}, payload={payload}")
            
        except Exception as e:
            logger.error(f"发送MQTT消息失败: {e}")
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.is_connected_flag and not self._closed
    
    async def close(self):
        """关闭连接"""
        if self._closed:
            return
            
        self._closed = True
        self.is_connected_flag = False
        
        # 取消心跳检查任务
        if self.keep_alive_task and not self.keep_alive_task.done():
            self.keep_alive_task.cancel()
            try:
                await self.keep_alive_task
            except asyncio.CancelledError:
                pass
        
        # 通知服务器连接关闭
        try:
            await self.mqtt_server.on_client_disconnected(self)
        except Exception as e:
            logger.error(f"通知服务器连接关闭失败: {e}")
        
        # 关闭协议处理器
        try:
            await self.protocol.close()
        except Exception as e:
            logger.error(f"关闭MQTT协议处理器失败: {e}")
        
        logger.info(f"MQTT连接已关闭: {self.client_id}")
