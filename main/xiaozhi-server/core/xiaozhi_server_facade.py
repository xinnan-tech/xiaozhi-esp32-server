#!/usr/bin/env python3
"""
小智服务器门面类
统一管理所有协议服务器的启动和停止
"""

import asyncio
from typing import Dict, Any, Optional
from config.logger import setup_logging
from config.config_loader import get_protocol_config, get_mqtt_server_config
from core.servers.multi_protocol_server import MultiProtocolServer

logger = setup_logging()
TAG = __name__


class XiaozhiServerFacade:
    """
    小智服务器门面类
    提供统一的服务器管理接口，屏蔽内部协议复杂性
    
    功能：
    - 协议管理（WebSocket、MQTT）
    - 本地 ASR 模型预加载
    - 优雅启动和停止
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化服务器门面
        
        Args:
            config: 服务器配置字典
        """
        self.config = config
        self.multi_protocol_server: Optional[MultiProtocolServer] = None
        self.shared_asr_manager = None  # 共享 ASR 管理器
        self.is_initialized = False
        self.is_running = False
        
        # 处理协议配置
        self._setup_protocol_config()
    
    def _setup_protocol_config(self):
        """设置协议配置"""
        try:
            # 获取协议配置
            try:
                protocol_config = get_protocol_config()
                mqtt_config = get_mqtt_server_config()
            except Exception as e:
                logger.warning(f"获取协议配置失败，使用默认配置: {e}")
                # 使用默认配置
                protocol_config = type('ProtocolConfig', (), {
                    'websocket_enabled': True,
                    'mqtt_enabled': False
                })()
                mqtt_config = type('MQTTConfig', (), {
                    'enabled': False,
                    'host': '0.0.0.0',
                    'port': 1883,
                    'udp_port': 1883,
                    'public_ip': 'localhost',
                    'max_connections': 1000,
                    'heartbeat_interval': 30,
                    'max_payload_size': 8192
                })()
            
            # 确定启用的协议
            enabled_protocols = []
            
            # WebSocket协议（默认启用）
            if getattr(protocol_config, 'websocket_enabled', True):
                enabled_protocols.append('websocket')
                logger.info("WebSocket协议已启用")
            
            # MQTT协议
            mqtt_enabled = (
                getattr(protocol_config, 'mqtt_enabled', False) or 
                getattr(mqtt_config, 'enabled', False)
            )
            if mqtt_enabled:
                enabled_protocols.append('mqtt')
                logger.info("MQTT协议已启用")
            
            # 如果没有启用任何协议，默认启用WebSocket
            if not enabled_protocols:
                logger.warning("没有启用任何协议，默认启用WebSocket")
                enabled_protocols = ['websocket']
            
            # 更新配置
            self.config['enabled_protocols'] = enabled_protocols
            
            # 添加MQTT服务器配置
            self.config['mqtt_server'] = {
                'enabled': getattr(mqtt_config, 'enabled', False),
                'host': getattr(mqtt_config, 'host', '0.0.0.0'),
                'port': getattr(mqtt_config, 'port', 1883),
                'udp_port': getattr(mqtt_config, 'udp_port', 1883),
                'public_ip': getattr(mqtt_config, 'public_ip', 'localhost'),
                'max_connections': getattr(mqtt_config, 'max_connections', 1000),
                'heartbeat_interval': getattr(mqtt_config, 'heartbeat_interval', 30),
                'max_payload_size': getattr(mqtt_config, 'max_payload_size', 8192)
            }
            
            logger.info(f"启用的协议: {enabled_protocols}")
            
        except Exception as e:
            logger.error(f"设置协议配置失败: {e}")
            # 使用最基本的配置
            self.config['enabled_protocols'] = ['websocket']
            self.config['mqtt_server'] = {
                'enabled': False,
                'host': '0.0.0.0',
                'port': 1883,
                'udp_port': 1883,
                'public_ip': 'localhost',
                'max_connections': 1000,
                'heartbeat_interval': 30,
                'max_payload_size': 8192
            }
    
    async def initialize(self):
        """初始化服务器"""
        if self.is_initialized:
            logger.bind(tag=TAG).warning("服务器已经初始化")
            return
        
        try:
            logger.bind(tag=TAG).info("正在初始化小智服务器...")
            
            # 检查并预加载本地 ASR 模型（关键步骤）
            await self._preload_asr_if_needed()
            
            # 创建多协议服务器
            self.multi_protocol_server = MultiProtocolServer(self.config)
            
            self.is_initialized = True
            logger.bind(tag=TAG).info("小智服务器初始化完成")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"初始化服务器失败: {e}")
            raise
    
    async def _preload_asr_if_needed(self):
        """
        检查并预加载本地 ASR 模型
        
        如果配置使用本地 ASR 模型（如 FunASR），则在服务器启动时预加载，
        避免首次语音识别时的延迟导致客户端超时。
        """
        try:
            # 获取 ASR 配置
            selected_asr = self.config.get("selected_module", {}).get("ASR")
            if not selected_asr:
                logger.bind(tag=TAG).info("未配置 ASR 模块，跳过预加载")
                return
            
            # 获取 ASR 类型
            asr_config = self.config.get("ASR", {}).get(selected_asr, {})
            asr_type = asr_config.get("type", selected_asr)
            
            # 导入 SharedASRManager 检查是否为本地模型
            from core.providers.asr.shared_asr_manager import SharedASRManager
            
            if SharedASRManager.is_local_model_type(asr_type):
                logger.bind(tag=TAG).info(
                    f"检测到本地 ASR 模型: {asr_type}，开始预加载..."
                )
                
                # 创建全局 ASR 管理器
                self.shared_asr_manager = SharedASRManager(self.config, asr_type)
                
                # 预加载模型
                await self.shared_asr_manager.initialize()
                
                # 将管理器放入配置中供后续使用
                self.config['_shared_asr_manager'] = self.shared_asr_manager
                
                logger.bind(tag=TAG).info(
                    f"ASR 模型预加载完成，类型: {asr_type}"
                )
            else:
                logger.bind(tag=TAG).info(
                    f"ASR 类型为远程服务: {asr_type}，无需预加载"
                )
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"ASR 预加载失败: {e}")
            # 预加载失败不影响服务器启动，继续使用懒加载模式
            logger.bind(tag=TAG).warning("将回退到懒加载模式")
    
    async def start(self):
        """启动服务器"""
        if not self.is_initialized:
            await self.initialize()
        
        if self.is_running:
            logger.warning("服务器已经在运行中")
            return
        
        try:
            logger.info("正在启动小智服务器...")
            
            # 启动多协议服务器
            await self.multi_protocol_server.start()
            
            self.is_running = True
            logger.info("小智服务器启动成功")
            
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            self.is_running = False
            raise
    
    async def stop(self):
        """停止服务器"""
        if not self.is_running:
            logger.bind(tag=TAG).info("服务器未在运行")
            return
        
        try:
            logger.bind(tag=TAG).info("正在停止小智服务器...")
            
            # 停止多协议服务器
            if self.multi_protocol_server:
                await self.multi_protocol_server.stop()
            
            # 关闭共享 ASR 管理器
            if self.shared_asr_manager:
                logger.bind(tag=TAG).info("正在关闭共享 ASR 管理器...")
                await self.shared_asr_manager.shutdown()
                self.shared_asr_manager = None
                # 从配置中移除
                if '_shared_asr_manager' in self.config:
                    del self.config['_shared_asr_manager']
            
            self.is_running = False
            logger.bind(tag=TAG).info("小智服务器已停止")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"停止服务器失败: {e}")
    
    async def restart(self):
        """重启服务器"""
        logger.info("重启小智服务器...")
        await self.stop()
        await asyncio.sleep(1)  # 等待清理完成
        await self.start()
    
    async def update_config(self, new_config: Dict[str, Any]) -> bool:
        """
        更新服务器配置
        
        Args:
            new_config: 新的配置字典
            
        Returns:
            bool: 更新是否成功
        """
        try:
            logger.info("更新服务器配置...")
            
            # 更新配置
            self.config.update(new_config)
            self._setup_protocol_config()
            
            # 如果服务器正在运行，更新多协议服务器配置
            if self.is_running and self.multi_protocol_server:
                success = await self.multi_protocol_server.update_config(self.config)
                if success:
                    logger.info("服务器配置更新成功")
                else:
                    logger.error("服务器配置更新失败")
                return success
            
            logger.info("配置更新完成（服务器未运行）")
            return True
            
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False
    
    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        base_status = {
            'is_initialized': self.is_initialized,
            'is_running': self.is_running,
            'enabled_protocols': self.config.get('enabled_protocols', [])
        }
        
        if self.multi_protocol_server:
            server_status = self.multi_protocol_server.get_server_status()
            base_status.update(server_status)
        
        # 添加 ASR 状态
        if self.shared_asr_manager:
            base_status['asr'] = {
                'mode': 'shared',
                'ready': self.shared_asr_manager.is_ready(),
                'queue_status': self.shared_asr_manager.get_queue_status()
            }
        else:
            base_status['asr'] = {'mode': 'lazy_load'}
        
        return base_status
    
    def get_active_connections_count(self) -> Dict[str, int]:
        """获取各协议的活跃连接数"""
        if self.multi_protocol_server:
            return self.multi_protocol_server.get_active_connections_count()
        return {}
    
    def get_supported_protocols(self) -> list:
        """获取支持的协议列表"""
        if self.multi_protocol_server:
            return self.multi_protocol_server.get_supported_protocols()
        return ['websocket', 'mqtt']
    
    def is_protocol_enabled(self, protocol: str) -> bool:
        """检查协议是否启用"""
        enabled_protocols = self.config.get('enabled_protocols', [])
        return protocol in enabled_protocols
    
    async def broadcast_message(self, message: Dict[str, Any], protocol: Optional[str] = None):
        """
        向所有连接广播消息
        
        Args:
            message: 要广播的消息
            protocol: 指定协议，None表示向所有协议广播
        """
        if self.multi_protocol_server:
            await self.multi_protocol_server.broadcast_message(message, protocol)
    
    def get_websocket_info(self) -> Dict[str, Any]:
        """获取WebSocket连接信息"""
        if not self.is_protocol_enabled('websocket'):
            return {'enabled': False}
        
        server_config = self.config.get('server', {})
        return {
            'enabled': True,
            'host': server_config.get('ip', '0.0.0.0'),
            'port': server_config.get('port', 8000),
            'path': '/xiaozhi/v1/'
        }
    
    def get_mqtt_info(self) -> Dict[str, Any]:
        """获取MQTT连接信息"""
        if not self.is_protocol_enabled('mqtt'):
            return {'enabled': False}
        
        mqtt_config = self.config.get('mqtt_server', {})
        return {
            'enabled': True,
            'host': mqtt_config.get('host', '0.0.0.0'),
            'port': mqtt_config.get('port', 1883),
            'udp_port': mqtt_config.get('udp_port', 1883),
            'public_ip': mqtt_config.get('public_ip', 'localhost')
        }
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取所有协议的连接信息"""
        return {
            'websocket': self.get_websocket_info(),
            'mqtt': self.get_mqtt_info(),
            'active_connections': self.get_active_connections_count()
        }

