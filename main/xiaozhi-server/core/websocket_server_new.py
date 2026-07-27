import asyncio
import logging
import json
import websockets
from typing import Dict, Any, Optional
from config.logger import setup_logging
from core.services.connection_service import ConnectionService
from core.transport.websocket_transport import WebSocketTransport
from config.config_loader import get_config_from_api_async
from core.utils.util import check_vad_update, check_asr_update
from core.auth import AuthMiddleware, AuthenticationError
from core.utils.config_validation import validate_config_components
from core.providers.asr.shared_asr_manager import SharedASRManager


class SuppressInvalidHandshakeFilter(logging.Filter):
    """过滤掉无效握手错误日志（如HTTPS访问WS端口）"""

    def filter(self, record):
        msg = record.getMessage()
        suppress_keywords = [
            "opening handshake failed",
            "did not receive a valid HTTP request",
            "connection closed while reading HTTP request",
            "line without CRLF",
        ]
        return not any(keyword in msg for keyword in suppress_keywords)


def _setup_websockets_logger():
    """配置 websockets 相关的所有 logger，过滤无效握手错误"""
    filter_instance = SuppressInvalidHandshakeFilter()
    for logger_name in ["websockets", "websockets.server", "websockets.client"]:
        ws_logger = logging.getLogger(logger_name)
        ws_logger.addFilter(filter_instance)


_setup_websockets_logger()


logger = setup_logging()
TAG = __name__


class NewWebSocketServer:
    """
    新的WebSocket服务器：使用新架构替代旧的ConnectionHandler
    集成ConnectionService、MessageRouter和新的Processor架构
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()
        self.config_lock = asyncio.Lock()
        self.last_update_error = None

        # 创建连接服务
        self.connection_service = ConnectionService(config)
        self.connection_service.server = self

        # 活跃连接管理
        self.active_connections = set()

        # 认证中间件
        self.auth_middleware = AuthMiddleware(config)

        # 服务器实例和控制
        self._server = None
        self._stop_event = asyncio.Event()
        self._started_event = asyncio.Event()
        self._is_running = False

    async def start(self):
        """启动WebSocket服务器"""
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("port", 8000))

        logger.bind(tag=TAG).info(f"启动新架构WebSocket服务器: {host}:{port}")

        self._stop_event.clear()
        self._started_event.clear()

        try:
            self._server = await websockets.serve(
                self._handle_connection,
                host,
                port,
                process_request=self._http_response
            )
            self._is_running = True
            self._started_event.set()
            logger.bind(tag=TAG).info("WebSocket服务器启动成功")

            # 等待停止信号
            await self._stop_event.wait()

        except Exception as e:
            logger.bind(tag=TAG).error(f"WebSocket服务器启动失败: {e}")
            raise
        finally:
            self._is_running = False
            self._started_event.clear()

    async def stop(self):
        """停止WebSocket服务器"""
        if not self._is_running:
            logger.bind(tag=TAG).debug("WebSocket服务器未运行，无需停止")
            return

        logger.bind(tag=TAG).info("正在停止WebSocket服务器...")

        # 关闭所有活跃连接
        for transport in list(self.active_connections):
            try:
                await transport.close()
            except Exception as e:
                logger.bind(tag=TAG).error(f"关闭连接失败: {e}")
        self.active_connections.clear()

        # 关闭服务器
        if self._server:
            self._server.close()
            try:
                await asyncio.wait_for(self._server.wait_closed(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.bind(tag=TAG).warning("等待服务器关闭超时")
            self._server = None

        # 发送停止信号
        self._stop_event.set()
        self._is_running = False
        self._started_event.clear()

        logger.bind(tag=TAG).info("WebSocket服务器已停止")

    async def _handle_connection(self, websocket):
        """处理新连接 - 使用新架构"""
        # 提取连接头信息
        headers = self._extract_headers(websocket)
        device_id = headers.get('device-id')

        # 如果没有 device-id，提示并关闭连接
        if not device_id:
            await websocket.send("端口正常，如需测试连接，请使用test_page.html")
            await websocket.close()
            return

        # 连接时认证
        try:
            await self._handle_auth(headers)
        except AuthenticationError as e:
            logger.bind(tag=TAG).warning(f"认证失败: {e}")
            await websocket.send("认证失败")
            await websocket.close()
            return

        # 创建WebSocket传输层
        try:
            protocol_version = int(headers.get('protocol-version', 1) or 1)
        except (TypeError, ValueError):
            protocol_version = 1
        transport = WebSocketTransport(
            websocket,
            from_mqtt_gateway=headers.get('from_mqtt_gateway') == 'true',
            protocol_version=protocol_version,
        )

        # 记录活跃连接
        self.active_connections.add(transport)

        try:
            logger.bind(tag=TAG).info(
                f"新连接建立: {device_id} from {headers.get('x-real-ip', 'unknown')}"
            )

            # 使用ConnectionService处理连接
            await self.connection_service.handle_connection(transport, headers)

        except websockets.exceptions.ConnectionClosed:
            logger.bind(tag=TAG).info("WebSocket连接正常关闭")
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理WebSocket连接时出错: {e}", exc_info=True)
            # 将错误反馈给管理端，避免长时间等待
            try:
                if hasattr(websocket, "closed") and not websocket.closed:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "error",
                                "message": f"Server error: {e}",
                                "content": {"action": "unknown"},
                            }
                        )
                    )
            except Exception:
                pass
        finally:
            # 确保从活动连接集合中移除
            self.active_connections.discard(transport)

            # 强制关闭连接（如果还没有关闭的话）
            try:
                if hasattr(websocket, "closed") and not websocket.closed:
                    await websocket.close()
                elif hasattr(websocket, "state") and websocket.state.name != "CLOSED":
                    await websocket.close()
            except Exception as close_error:
                logger.bind(tag=TAG).error(f"强制关闭WebSocket连接时出错: {close_error}")

    async def _handle_auth(self, headers: Dict[str, str]):
        """
        连接时认证

        Args:
            headers: HTTP 请求头

        Raises:
            AuthenticationError: 认证失败时抛出
        """
        await self.auth_middleware.authenticate_async(headers)

    def _extract_headers(self, websocket) -> Dict[str, str]:
        """
        从WebSocket请求中提取头信息

        支持从以下来源提取信息：
        1. HTTP 请求头
        2. URL 查询参数（device-id, client-id, authorization）
        3. 路径参数（如 ?from=mqtt_gateway）
        """
        headers = {}

        # 1. 提取 HTTP 请求头
        if hasattr(websocket, 'request') and hasattr(websocket.request, 'headers'):
            for name, value in websocket.request.headers.items():
                headers[name.lower()] = value
        elif hasattr(websocket, 'request_headers'):
            for name, value in websocket.request_headers.items():
                headers[name.lower()] = value

        # 2. 提取路径参数（如果有的话）
        request_path = None
        if hasattr(websocket, 'request') and hasattr(websocket.request, 'path'):
            request_path = websocket.request.path
        elif hasattr(websocket, 'path'):
            request_path = websocket.path

        if request_path:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(request_path)
            query_params = parse_qs(parsed.query)

            # 处理关键参数：device-id, client-id, authorization
            key_params = ['device-id', 'client-id', 'authorization']
            for key in key_params:
                if key in query_params and query_params[key]:
                    # URL 参数优先级低于 header
                    if key not in headers or not headers[key]:
                        headers[key] = query_params[key][0]

            # 处理其他参数
            for key, values in query_params.items():
                if values and key not in headers:
                    headers[key] = values[0]

            # 检查是否来自 MQTT 网关
            if request_path.endswith("?from=mqtt_gateway") or "from=mqtt_gateway" in request_path:
                headers['from_mqtt_gateway'] = 'true'

        # 3. 提取远程地址
        if hasattr(websocket, 'remote_address'):
            # 如果 headers 中没有 x-real-ip，使用 remote_address
            if 'x-real-ip' not in headers:
                headers['x-real-ip'] = websocket.remote_address[0]

        return headers

    async def _http_response(self, websocket, request_headers):
        """处理HTTP请求"""
        # 检查是否为 WebSocket 升级请求
        if request_headers.headers.get("connection", "").lower() == "upgrade":
            # 如果是 WebSocket 请求，返回 None 允许握手继续
            return None
        else:
            # 如果是普通 HTTP 请求，返回服务器状态
            return websocket.respond(200, "New Architecture WebSocket Server is running\n")

    async def apply_config(self, new_config: Dict[str, Any]) -> bool:
        """Apply a facade-validated config to future WebSocket connections."""
        self.config = new_config
        self.connection_service = ConnectionService(new_config)
        self.connection_service.server = getattr(self, "management_owner", self)
        self.auth_middleware = AuthMiddleware(new_config)
        return True

    async def update_config(
        self, new_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新服务器配置并重新初始化组件

        Returns:
            bool: 更新是否成功
        """
        try:
            async with self.config_lock:
                logger.bind(tag=TAG).info("开始更新服务器配置")
                self.last_update_error = None
                old_config = self.config
                old_connection_service = self.connection_service
                old_auth_middleware = self.auth_middleware

                # 管理命令可自行拉取配置；多协议管理器则直接传入已合并配置。
                if new_config is None:
                    new_config = await get_config_from_api_async(self.config)
                    if new_config is None:
                        logger.bind(tag=TAG).error("获取新配置失败")
                        self.last_update_error = "获取新配置失败"
                        return False

                logger.bind(tag=TAG).info("获取新配置成功")

                new_shared_manager = None
                reuse_manager = False

                # 校验新配置（预初始化组件以发现配置错误）
                ok, error_msg = await validate_config_components(new_config, logger)
                if not ok:
                    logger.bind(tag=TAG).error(f"配置校验失败: {error_msg}")
                    self.last_update_error = f"配置校验失败: {error_msg}"
                    return False

                # 准备共享 ASR 管理器（本地模型走共享预加载）
                old_shared_manager = old_config.get("_shared_asr_manager")
                selected_asr = new_config.get("selected_module", {}).get("ASR")
                if selected_asr:
                    asr_config = new_config.get("ASR", {}).get(selected_asr, {})
                    asr_type = asr_config.get("type", selected_asr)
                    if SharedASRManager.is_local_model_type(asr_type):
                        if (
                            old_shared_manager
                            and getattr(old_shared_manager, "asr_type", None) == asr_type
                            and old_shared_manager.is_ready()
                        ):
                            new_shared_manager = old_shared_manager
                            reuse_manager = True
                        else:
                            new_shared_manager = SharedASRManager(new_config, asr_type)
                            await new_shared_manager.initialize()
                # 非本地模型时不立即关闭旧共享管理器，待更新成功后统一处理

                # 检查 VAD 和 ASR 类型是否需要更新
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)
                logger.bind(tag=TAG).info(
                    f"检查VAD和ASR类型是否需要更新: VAD={update_vad}, ASR={update_asr}"
                )

                # 检查配置是否有重大变化
                changed_configs = self._get_changed_configs(self.config, new_config)

                # 更新配置
                self.config = new_config
                if new_shared_manager:
                    self.config["_shared_asr_manager"] = new_shared_manager
                elif "_shared_asr_manager" in self.config:
                    del self.config["_shared_asr_manager"]

                # 根据变化类型进行更新
                if changed_configs:
                    logger.bind(tag=TAG).info(f"配置项变化: {', '.join(changed_configs)}")

                # 重新创建连接服务，使用新配置
                # 注意：已建立的连接会继续使用旧配置，只有新连接使用新配置
                self.connection_service = ConnectionService(new_config)
                self.connection_service.server = self

                # 如果 ASR 配置变化且复用旧共享管理器，提示重启
                if update_asr and reuse_manager:
                    logger.bind(tag=TAG).warning(
                        "ASR 配置已变化，但仍复用已有共享 ASR 管理器，建议重启服务"
                    )
                else:
                    # 即使没有重大变化，也更新 ConnectionService 的配置引用
                    self.connection_service.config = new_config
                    self.connection_service.server = self

                # 更新认证中间件
                self.auth_middleware = AuthMiddleware(new_config)

                # 更新成功后再关闭旧共享管理器（避免失败回滚时不可用）
                if old_shared_manager and old_shared_manager is not new_shared_manager:
                    await old_shared_manager.shutdown()

                logger.bind(tag=TAG).info("配置更新任务执行完毕")
                return True

        except Exception as e:
            logger.bind(tag=TAG).error(f"更新服务器配置失败: {str(e)}", exc_info=True)
            self.last_update_error = f"更新服务器配置失败: {str(e)}"
            try:
                if new_shared_manager and not reuse_manager:
                    await new_shared_manager.shutdown()
                self.config = old_config
                self.connection_service = old_connection_service
                self.auth_middleware = old_auth_middleware
            except Exception:
                pass
            return False

    def get_last_update_error(self) -> str:
        return self.last_update_error or ""

    def _get_changed_configs(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> list:
        """
        获取变化的配置项列表

        Returns:
            list: 变化的配置项名称列表
        """
        changed = []
        key_configs = [
            "selected_module",
            "VAD",
            "ASR",
            "LLM",
            "TTS",
            "Memory",
            "Intent"
        ]

        for key in key_configs:
            old_value = old_config.get(key)
            new_value = new_config.get(key)
            if old_value != new_value:
                changed.append(key)

        return changed

    def get_active_connections_count(self) -> int:
        """获取活跃连接数"""
        return len(self.active_connections)

    def get_server_status(self) -> Dict[str, Any]:
        """获取服务器状态"""
        return {
            "active_connections": self.get_active_connections_count(),
            "server_type": "new_architecture",
            "processors": self.connection_service.message_router.list_processors()
        }
