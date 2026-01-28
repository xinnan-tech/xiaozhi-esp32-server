import asyncio
import socket
import time
from typing import Dict, Any, Set
from config.logger import setup_logging
from core.protocols.mqtt_connection import MQTTConnection
from core.transport.mqtt_transport import MQTTTransport, UDPAudioHandler
from core.services.connection_service import ConnectionService

logger = setup_logging()


class MQTTServer:
    """
    原生MQTT服务器：直接处理MQTT协议连接
    集成到xiaozhi-server架构中
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        
        # 服务器配置
        server_config = config.get('mqtt_server', {})
        self.mqtt_port = server_config.get('port', 1883)
        self.udp_port = server_config.get('udp_port', self.mqtt_port)
        self.host = server_config.get('host', '0.0.0.0')
        self.public_ip = server_config.get('public_ip', 'localhost')
        
        # 连接管理
        self.connections: Dict[int, MQTTConnection] = {}
        self.udp_handlers: Dict[int, UDPAudioHandler] = {}
        self.connection_id_counter = 0
        
        # 服务器实例
        self.mqtt_server = None
        self.udp_server = None
        
        # 连接服务
        self.connection_service = ConnectionService(config)
        
        # 活跃连接管理
        self.active_transports: Set[MQTTTransport] = set()
        
        # 心跳检查
        self.heartbeat_task = None
        self.heartbeat_interval = 30  # 30秒检查一次
    
    async def start(self):
        """启动MQTT服务器"""
        try:
            # 启动MQTT TCP服务器
            await self._start_mqtt_server()
            
            # 启动UDP服务器
            await self._start_udp_server()
            
            # 启动心跳检查
            self.heartbeat_task = asyncio.create_task(self._heartbeat_check())
            
            logger.info(f"MQTT服务器启动成功: {self.host}:{self.mqtt_port}")
            logger.info(f"UDP服务器启动成功: {self.host}:{self.udp_port}")
            
        except Exception as e:
            logger.error(f"启动MQTT服务器失败: {e}")
            raise
    
    async def _start_mqtt_server(self):
        """启动MQTT TCP服务器"""
        self.mqtt_server = await asyncio.start_server(
            self._handle_mqtt_connection,
            self.host,
            self.mqtt_port
        )
    
    async def _start_udp_server(self):
        """启动UDP服务器"""
        loop = asyncio.get_event_loop()
        
        # 创建UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.host, self.udp_port))
        sock.setblocking(False)
        
        # 创建UDP协议处理器
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPProtocol(self),
            sock=sock
        )
        
        self.udp_server = (transport, protocol)
    
    async def _handle_mqtt_connection(self, reader, writer):
        """处理新的MQTT连接"""
        connection_id = self._generate_connection_id()
        
        try:
            # 获取客户端地址
            client_addr = writer.get_extra_info('peername')
            logger.info(f"新MQTT连接: {client_addr}, connection_id: {connection_id}")
            
            # 创建MQTT连接处理器
            mqtt_connection = MQTTConnection(
                writer.get_extra_info('socket'),
                connection_id,
                self
            )
            
            # 创建UDP音频处理器
            udp_handler = UDPAudioHandler(
                connection_id,
                self,
                {}  # 加密配置将在hello消息中设置
            )
            
            # 创建MQTT传输层
            transport = MQTTTransport(mqtt_connection, udp_handler)
            
            # 注册连接
            self.connections[connection_id] = mqtt_connection
            self.udp_handlers[connection_id] = udp_handler
            self.active_transports.add(transport)
            
            # 提取连接头信息
            headers = {
                'x-real-ip': client_addr[0] if client_addr else 'unknown',
                'connection-type': 'mqtt'
            }
            
            try:
                # 使用ConnectionService处理连接
                await self.connection_service.handle_connection(transport, headers)
                
            except Exception as e:
                logger.error(f"ConnectionService处理MQTT连接失败: {e}")
            
        except Exception as e:
            logger.error(f"处理MQTT连接失败: {e}")
        finally:
            # 清理连接
            await self._cleanup_connection(connection_id)
    
    async def _cleanup_connection(self, connection_id: int):
        """清理连接资源"""
        try:
            # 移除连接
            if connection_id in self.connections:
                connection = self.connections.pop(connection_id)
                await connection.close()
            
            # 移除UDP处理器
            if connection_id in self.udp_handlers:
                udp_handler = self.udp_handlers.pop(connection_id)
                await udp_handler.close()
            
            # 移除传输层（通过连接ID查找）
            transports_to_remove = []
            for transport in self.active_transports:
                if hasattr(transport, '_mqtt_connection') and \
                   transport._mqtt_connection.connection_id == connection_id:
                    transports_to_remove.append(transport)
            
            for transport in transports_to_remove:
                self.active_transports.discard(transport)
                await transport.close()
            
            logger.info(f"MQTT连接清理完成: {connection_id}")
            
        except Exception as e:
            logger.error(f"清理MQTT连接失败: {e}")
    
    def _generate_connection_id(self) -> int:
        """生成连接ID"""
        self.connection_id_counter += 1
        return self.connection_id_counter
    
    async def on_client_connected(self, mqtt_connection: MQTTConnection):
        """客户端连接回调"""
        logger.info(f"MQTT客户端已连接: {mqtt_connection.client_id}")
    
    async def on_client_disconnected(self, mqtt_connection: MQTTConnection):
        """客户端断开连接回调"""
        logger.info(f"MQTT客户端已断开: {mqtt_connection.client_id}")
    
    async def send_udp_message(self, data: bytes, remote_addr: tuple):
        """发送UDP消息"""
        if self.udp_server:
            transport, protocol = self.udp_server
            transport.sendto(data, remote_addr)
    
    async def send_encrypted_audio(self, connection_id: int, audio_data: bytes, 
                                 timestamp: int, remote_addr: tuple, encryption_config: Dict[str, Any]):
        """发送加密音频数据"""
        try:
            # 这里应该实现音频数据加密逻辑
            # 暂时直接发送原始数据
            header = self._generate_udp_header(connection_id, len(audio_data), timestamp, 0)
            message = header + audio_data
            
            await self.send_udp_message(message, remote_addr)
            
        except Exception as e:
            logger.error(f"发送加密音频失败: {e}")
    
    def _generate_udp_header(self, connection_id: int, length: int, timestamp: int, sequence: int) -> bytes:
        """生成UDP消息头"""
        header = bytearray(16)
        header[0] = 1  # type
        header[2:4] = length.to_bytes(2, 'big')  # payload length
        header[4:8] = connection_id.to_bytes(4, 'big')  # connection id
        header[8:12] = timestamp.to_bytes(4, 'big')  # timestamp
        header[12:16] = sequence.to_bytes(4, 'big')  # sequence
        return bytes(header)
    
    async def _heartbeat_check(self):
        """心跳检查任务"""
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                
                # 检查所有连接的状态
                dead_connections = []
                for connection_id, connection in self.connections.items():
                    if not connection.is_connected():
                        dead_connections.append(connection_id)
                
                # 清理死连接
                for connection_id in dead_connections:
                    logger.info(f"清理死连接: {connection_id}")
                    await self._cleanup_connection(connection_id)
                
                # 记录活跃连接数
                active_count = len(self.connections)
                if active_count > 0:
                    logger.info(f"MQTT活跃连接数: {active_count}")
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"心跳检查任务出错: {e}")
    
    async def stop(self):
        """停止MQTT服务器"""
        logger.info("正在停止MQTT服务器...")
        
        # 停止心跳检查
        if self.heartbeat_task and not self.heartbeat_task.done():
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # 关闭所有连接
        for connection_id in list(self.connections.keys()):
            await self._cleanup_connection(connection_id)
        
        # 关闭UDP服务器
        if self.udp_server:
            transport, protocol = self.udp_server
            transport.close()
        
        # 关闭MQTT服务器
        if self.mqtt_server:
            self.mqtt_server.close()
            await self.mqtt_server.wait_closed()
        
        logger.info("MQTT服务器已停止")
    
    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        return {
            'type': 'mqtt',
            'host': self.host,
            'mqtt_port': self.mqtt_port,
            'udp_port': self.udp_port,
            'active_connections': len(self.connections),
            'active_transports': len(self.active_transports)
        }


class UDPProtocol(asyncio.DatagramProtocol):
    """UDP协议处理器"""
    
    def __init__(self, mqtt_server: MQTTServer):
        self.mqtt_server = mqtt_server
        self.transport = None
    
    def connection_made(self, transport):
        self.transport = transport
    
    def datagram_received(self, data: bytes, addr: tuple):
        """接收UDP数据报"""
        try:
            # 解析UDP消息头
            if len(data) < 16:
                return
            
            connection_id = int.from_bytes(data[4:8], 'big')
            timestamp = int.from_bytes(data[8:12], 'big')
            sequence = int.from_bytes(data[12:16], 'big')
            payload = data[16:]
            
            # 找到对应的UDP处理器
            udp_handler = self.mqtt_server.udp_handlers.get(connection_id)
            if udp_handler:
                udp_handler.on_udp_message(payload, timestamp, addr)
            
        except Exception as e:
            logger.error(f"处理UDP数据报失败: {e}")
    
    def error_received(self, exc):
        logger.error(f"UDP协议错误: {exc}")

