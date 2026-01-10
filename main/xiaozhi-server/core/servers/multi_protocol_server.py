import asyncio
from typing import Dict, Any, List, Optional
from config.logger import setup_logging
from core.websocket_server_new import NewWebSocketServer
from core.servers.mqtt_server import MQTTServer

logger = setup_logging()


class MultiProtocolServer:
    """
    多协议服务器管理器：统一管理WebSocket和MQTT服务器
    提供统一的启动、停止和状态监控接口
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        
        # 服务器实例
        self.servers: Dict[str, Any] = {}
        self.server_tasks: Dict[str, asyncio.Task] = {}
        
        # 服务器状态
        self.is_running = False
        self.startup_complete = False
        
        # 初始化服务器
        self._initialize_servers()
    
    def _initialize_servers(self):
        """初始化所有协议服务器"""
        try:
            # 检查配置中启用的协议
            enabled_protocols = self.config.get('enabled_protocols', ['websocket'])
            
            # 初始化WebSocket服务器
            if 'websocket' in enabled_protocols:
                self.servers['websocket'] = NewWebSocketServer(self.config)
                logger.info("WebSocket服务器已初始化")
            
            # 初始化MQTT服务器
            if 'mqtt' in enabled_protocols:
                self.servers['mqtt'] = MQTTServer(self.config)
                logger.info("MQTT服务器已初始化")
            
            if not self.servers:
                logger.warning("没有启用任何协议服务器")
            
        except Exception as e:
            logger.error(f"初始化服务器失败: {e}")
            raise
    
    async def start(self):
        """启动所有服务器"""
        if self.is_running:
            logger.warning("服务器已经在运行中")
            return
        
        try:
            logger.info("开始启动多协议服务器...")
            self.is_running = True
            
            # 启动所有服务器
            for protocol, server in self.servers.items():
                try:
                    logger.info(f"启动{protocol}服务器...")
                    task = asyncio.create_task(server.start())
                    self.server_tasks[protocol] = task
                    
                    # 等待一小段时间确保服务器启动
                    await asyncio.sleep(0.1)
                    
                    logger.info(f"{protocol}服务器启动成功")
                    
                except Exception as e:
                    logger.error(f"启动{protocol}服务器失败: {e}")
                    # 继续启动其他服务器
                    continue
            
            self.startup_complete = True
            logger.info("多协议服务器启动完成")
            
            # 启动监控任务
            asyncio.create_task(self._monitor_servers())
            
            # 等待所有服务器任务
            if self.server_tasks:
                await asyncio.gather(*self.server_tasks.values(), return_exceptions=True)
            
        except Exception as e:
            logger.error(f"启动多协议服务器失败: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """停止所有服务器"""
        if not self.is_running:
            return
        
        logger.info("开始停止多协议服务器...")
        self.is_running = False
        
        # 停止所有服务器
        for protocol, server in self.servers.items():
            try:
                logger.info(f"停止{protocol}服务器...")
                await server.stop()
                logger.info(f"{protocol}服务器已停止")
            except Exception as e:
                logger.error(f"停止{protocol}服务器失败: {e}")
        
        # 取消所有服务器任务
        for protocol, task in self.server_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self.server_tasks.clear()
        logger.info("多协议服务器已停止")
    
    async def restart(self):
        """重启所有服务器"""
        logger.info("重启多协议服务器...")
        await self.stop()
        await asyncio.sleep(1)  # 等待清理完成
        await self.start()
    
    async def restart_server(self, protocol: str):
        """重启指定协议的服务器"""
        if protocol not in self.servers:
            logger.error(f"未找到协议服务器: {protocol}")
            return False
        
        try:
            logger.info(f"重启{protocol}服务器...")
            
            # 停止指定服务器
            server = self.servers[protocol]
            await server.stop()
            
            # 取消任务
            if protocol in self.server_tasks:
                task = self.server_tasks[protocol]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # 重新启动
            task = asyncio.create_task(server.start())
            self.server_tasks[protocol] = task
            
            logger.info(f"{protocol}服务器重启成功")
            return True
            
        except Exception as e:
            logger.error(f"重启{protocol}服务器失败: {e}")
            return False
    
    async def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        try:
            logger.info("更新多协议服务器配置...")
            
            # 检查配置变化
            config_changed = self._check_config_changes(self.config, new_config)
            
            # 更新配置
            self.config = new_config
            
            # 如果配置有重大变化，重新初始化服务器
            if config_changed:
                logger.info("配置有重大变化，重新初始化服务器...")
                await self.stop()
                self._initialize_servers()
                if self.is_running:
                    await self.start()
            else:
                # 更新各个服务器的配置
                for protocol, server in self.servers.items():
                    if hasattr(server, 'update_config'):
                        await server.update_config(new_config)
            
            logger.info("配置更新完成")
            return True
            
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            return False
    
    def _check_config_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> bool:
        """检查配置是否有重大变化"""
        # 检查启用的协议是否变化
        old_protocols = set(old_config.get('enabled_protocols', ['websocket']))
        new_protocols = set(new_config.get('enabled_protocols', ['websocket']))
        
        if old_protocols != new_protocols:
            logger.info(f"启用协议发生变化: {old_protocols} -> {new_protocols}")
            return True
        
        # 检查服务器端口配置
        server_configs = ['server', 'mqtt_server']
        for config_key in server_configs:
            old_server_config = old_config.get(config_key, {})
            new_server_config = new_config.get(config_key, {})
            
            # 检查端口和主机配置
            for key in ['port', 'host', 'ip']:
                if old_server_config.get(key) != new_server_config.get(key):
                    logger.info(f"服务器配置{config_key}.{key}发生变化")
                    return True
        
        return False
    
    async def _monitor_servers(self):
        """监控服务器状态"""
        try:
            while self.is_running:
                await asyncio.sleep(30)  # 每30秒检查一次
                
                # 检查服务器任务状态
                for protocol, task in self.server_tasks.items():
                    if task.done():
                        exception = task.exception()
                        if exception:
                            logger.error(f"{protocol}服务器异常退出: {exception}")
                            # 尝试重启服务器
                            await self.restart_server(protocol)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"服务器监控任务出错: {e}")
    
    def get_server_status(self) -> Dict[str, Any]:
        """获取所有服务器状态"""
        status = {
            'is_running': self.is_running,
            'startup_complete': self.startup_complete,
            'enabled_protocols': list(self.servers.keys()),
            'servers': {}
        }
        
        # 获取各个服务器的状态
        for protocol, server in self.servers.items():
            try:
                if hasattr(server, 'get_server_status'):
                    server_status = server.get_server_status()
                else:
                    server_status = {'type': protocol, 'status': 'unknown'}
                
                # 添加任务状态
                task = self.server_tasks.get(protocol)
                if task:
                    server_status['task_status'] = 'running' if not task.done() else 'stopped'
                    if task.done() and task.exception():
                        server_status['task_error'] = str(task.exception())
                
                status['servers'][protocol] = server_status
                
            except Exception as e:
                status['servers'][protocol] = {
                    'type': protocol,
                    'status': 'error',
                    'error': str(e)
                }
        
        return status
    
    def get_active_connections_count(self) -> Dict[str, int]:
        """获取各协议的活跃连接数"""
        connections = {}
        
        for protocol, server in self.servers.items():
            try:
                if hasattr(server, 'get_active_connections_count'):
                    connections[protocol] = server.get_active_connections_count()
                elif hasattr(server, 'connections'):
                    connections[protocol] = len(server.connections)
                else:
                    connections[protocol] = 0
            except Exception as e:
                logger.error(f"获取{protocol}连接数失败: {e}")
                connections[protocol] = -1
        
        return connections
    
    async def broadcast_message(self, message: Dict[str, Any], protocol: Optional[str] = None):
        """向所有连接广播消息"""
        try:
            if protocol:
                # 向指定协议广播
                if protocol in self.servers:
                    server = self.servers[protocol]
                    if hasattr(server, 'broadcast_message'):
                        await server.broadcast_message(message)
            else:
                # 向所有协议广播
                for server in self.servers.values():
                    if hasattr(server, 'broadcast_message'):
                        await server.broadcast_message(message)
                        
        except Exception as e:
            logger.error(f"广播消息失败: {e}")
    
    def get_supported_protocols(self) -> List[str]:
        """获取支持的协议列表"""
        return ['websocket', 'mqtt']
    
    def is_protocol_enabled(self, protocol: str) -> bool:
        """检查协议是否启用"""
        return protocol in self.servers

