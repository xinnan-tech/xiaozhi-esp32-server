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
        self.monitor_task: Optional[asyncio.Task] = None
        self._lifecycle_lock = asyncio.Lock()
        self.management_owner = None

        # 服务器状态
        self.is_running = False
        self.startup_complete = False

        # 初始化服务器
        self._initialize_servers()

    def _initialize_servers(self):
        """初始化所有协议服务器"""
        try:
            self.servers.clear()
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

            for server in self.servers.values():
                self._bind_management_owner(server)

        except Exception as e:
            logger.error(f"初始化服务器失败: {e}")
            raise

    def set_management_owner(self, owner: Any) -> None:
        """Route management commands through the facade that owns all protocols."""
        self.management_owner = owner
        for server in self.servers.values():
            self._bind_management_owner(server)

    def _bind_management_owner(self, server: Any) -> None:
        owner = self.management_owner or server
        server.management_owner = owner
        connection_service = getattr(server, "connection_service", None)
        if connection_service is not None:
            connection_service.server = owner

    async def start(self):
        """启动所有服务器，并由管理器持有协议任务。"""
        async with self._lifecycle_lock:
            await self._start_unlocked()

    async def _start_unlocked(self):
        if self.is_running:
            logger.warning("服务器已经在运行中")
            return
        if self.server_tasks:
            raise RuntimeError("上次协议停止尚未完成，请先重试 stop 清理残留资源")

        try:
            logger.info("开始启动多协议服务器...")
            self.is_running = True
            self.startup_complete = False

            # 启动所有服务器
            for protocol, server in self.servers.items():
                try:
                    logger.info(f"启动{protocol}服务器...")
                    task = asyncio.create_task(
                        server.start(), name=f"xiaozhi-{protocol}-server"
                    )
                    self.server_tasks[protocol] = task
                    await self._wait_for_server_started(protocol, server, task)

                    logger.info(f"{protocol}服务器启动成功")

                except Exception as e:
                    logger.error(f"启动{protocol}服务器失败: {e}")
                    raise

            self.startup_complete = True
            logger.info("多协议服务器启动完成")

            # 启动监控任务；必须保存引用，以便停止和重启时回收。
            self.monitor_task = asyncio.create_task(
                self._monitor_servers(), name="xiaozhi-protocol-monitor"
            )

        except Exception as e:
            logger.error(f"启动多协议服务器失败: {e}")
            try:
                await self._stop_unlocked()
            except Exception as cleanup_error:
                logger.error(f"启动失败后的协议清理失败: {cleanup_error}")
            raise

    async def _wait_for_server_started(self, protocol, server, task):
        """等待协议监听器真正就绪，而不是依赖固定 sleep。"""
        started_event = getattr(server, "_started_event", None)
        if not isinstance(started_event, asyncio.Event):
            await asyncio.sleep(0)
            if task.done():
                await task
            return

        timeout = float(self.config.get("server_startup_timeout", 10))
        event_waiter = asyncio.create_task(started_event.wait())
        try:
            done, _ = await asyncio.wait(
                {task, event_waiter},
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if started_event.is_set():
                if task.done():
                    await task
                return
            if task in done:
                await task
                raise RuntimeError(f"{protocol}服务器在就绪前退出")
            raise TimeoutError(f"等待{protocol}服务器启动超时")
        finally:
            if not event_waiter.done():
                event_waiter.cancel()
                try:
                    await event_waiter
                except asyncio.CancelledError:
                    pass

    async def stop(self):
        """停止所有服务器"""
        async with self._lifecycle_lock:
            await self._stop_unlocked()

    async def _stop_unlocked(self):
        if not self.is_running and not self.server_tasks and not self.monitor_task:
            return

        logger.info("开始停止多协议服务器...")
        self.is_running = False
        self.startup_complete = False

        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        self.monitor_task = None

        # 停止所有服务器
        errors = []
        stopped_protocols = []
        for protocol, server in self.servers.items():
            try:
                logger.info(f"停止{protocol}服务器...")
                stopped = await server.stop()
                if stopped is False:
                    raise RuntimeError("协议仍有取消不响应的后台任务")
                logger.info(f"{protocol}服务器已停止")
                stopped_protocols.append(protocol)
            except Exception as e:
                logger.error(f"停止{protocol}服务器失败: {e}")
                errors.append((protocol, e))

        # 只释放已确认停止的任务。失败协议保留所有权，允许再次 stop。
        for protocol in stopped_protocols:
            task = self.server_tasks.get(protocol)
            if task is None:
                continue
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    errors.append((f"{protocol}任务", e))
                    logger.error(f"回收{protocol}服务器任务失败: {e}")
                    continue
            self.server_tasks.pop(protocol, None)

        if errors:
            details = ", ".join(
                f"{protocol}: {error}" for protocol, error in errors
            )
            raise RuntimeError(f"停止协议服务器时发生错误: {details}")
        logger.info("多协议服务器已停止")

    async def restart(self):
        """重启所有服务器"""
        async with self._lifecycle_lock:
            logger.info("重启多协议服务器...")
            await self._stop_unlocked()
            await self._start_unlocked()

    async def restart_server(self, protocol: str):
        """重启指定协议的服务器"""
        async with self._lifecycle_lock:
            return await self._restart_server_unlocked(protocol)

    async def _restart_server_unlocked(self, protocol: str):
        if protocol not in self.servers:
            logger.error(f"未找到协议服务器: {protocol}")
            return False

        try:
            logger.info(f"重启{protocol}服务器...")

            # 停止指定服务器
            server = self.servers[protocol]
            stopped = await server.stop()
            if stopped is False:
                raise RuntimeError("协议仍有取消不响应的后台任务")

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
            task = asyncio.create_task(
                server.start(), name=f"xiaozhi-{protocol}-server"
            )
            self.server_tasks[protocol] = task
            await self._wait_for_server_started(protocol, server, task)

            logger.info(f"{protocol}服务器重启成功")
            return True

        except Exception as e:
            logger.error(f"重启{protocol}服务器失败: {e}")
            return False

    async def update_config(self, new_config: Dict[str, Any]):
        """更新配置"""
        async with self._lifecycle_lock:
            return await self._update_config_unlocked(new_config)

    async def _update_config_unlocked(self, new_config: Dict[str, Any]):
        old_config = self.config
        was_running = self.is_running
        config_changed = False
        old_runtime_stopped = False
        try:
            logger.info("更新多协议服务器配置...")
            # 检查配置变化
            config_changed = self._check_config_changes(self.config, new_config)

            # 如果配置有重大变化，重新初始化服务器
            if config_changed:
                logger.info("配置有重大变化，重新初始化服务器...")
                await self._stop_unlocked()
                old_runtime_stopped = True
                self.config = new_config
                self._initialize_servers()
                if was_running:
                    await self._start_unlocked()
            else:
                # 更新各个服务器的配置
                for protocol, server in self.servers.items():
                    updated = True
                    if hasattr(server, 'apply_config'):
                        updated = await server.apply_config(new_config)
                    elif hasattr(server, 'update_config'):
                        updated = await server.update_config(new_config)
                    if updated is False:
                        raise RuntimeError(f"{protocol}配置更新失败")
                    self._bind_management_owner(server)
                self.config = new_config

            logger.info("配置更新完成")
            return True

        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            if config_changed and not old_runtime_stopped:
                # A listener still owns resources. Preserve the old server
                # objects/tasks so stop can be retried safely.
                self.config = old_config
                return False
            try:
                await self._stop_unlocked()
                self.config = old_config
                self._initialize_servers()
                if was_running:
                    await self._start_unlocked()
            except Exception:
                logger.exception("回滚多协议服务器配置失败")
            return False

    def _check_config_changes(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> bool:
        """检查配置是否有重大变化"""
        # 检查启用的协议是否变化
        old_protocols = set(old_config.get('enabled_protocols', ['websocket']))
        new_protocols = set(new_config.get('enabled_protocols', ['websocket']))

        if old_protocols != new_protocols:
            logger.info(f"启用协议发生变化: {old_protocols} -> {new_protocols}")
            return True

        if old_config.get("_shared_asr_manager") is not new_config.get(
            "_shared_asr_manager"
        ):
            logger.info("共享ASR管理器发生变化")
            return True

        # 检查服务器端口配置
        server_configs = {
            'server': ('port', 'host', 'ip'),
            'mqtt_server': (
                'port',
                'udp_port',
                'host',
                'ip',
                'public_endpoint',
                'udp_bind_host',
            ),
        }
        for config_key, listener_keys in server_configs.items():
            old_server_config = old_config.get(config_key, {})
            new_server_config = new_config.get(config_key, {})

            # 检查端口和主机配置
            for key in listener_keys:
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
                for protocol, task in list(self.server_tasks.items()):
                    if task.done():
                        exception = None if task.cancelled() else task.exception()
                        if exception:
                            logger.error(f"{protocol}服务器异常退出: {exception}")
                        else:
                            logger.warning(f"{protocol}服务器任务意外退出")
                        # 监控任务本身不能重入 lifecycle lock。
                        async with self._lifecycle_lock:
                            if self.is_running:
                                await self._restart_server_unlocked(protocol)

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
                    if task.done() and not task.cancelled() and task.exception():
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
