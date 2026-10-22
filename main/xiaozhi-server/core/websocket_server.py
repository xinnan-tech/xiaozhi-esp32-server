import asyncio
import logging

import websockets
from config.logger import setup_logging


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
        logger = logging.getLogger(logger_name)
        logger.addFilter(filter_instance)


_setup_websockets_logger()


from core.connection import ConnectionHandler
from config.config_loader import get_config_from_api_async
from core.auth import AuthManager, AuthenticationError
from core.utils.modules_initialize import initialize_modules
from core.utils.util import check_vad_update, check_asr_update

TAG = __name__

# 浏览器不能自定义 websocket 请求头，约定把凭证和设备标识放进子协议头：
# Sec-WebSocket-Protocol: xiaozhi, t-<token>, d-<deviceId>, c-<clientId>
# 握手时只回显 xiaozhi，其余值由服务端自己解析。加前缀是为了让每个值
# 都落在合法的子协议 token 字符集内（deviceId 的冒号就不合法）
WS_SUBPROTOCOL = "xiaozhi"
WS_SUBPROTOCOL_FIELDS = (("t-", "authorization"), ("d-", "device-id"), ("c-", "client-id"))


def _parse_subprotocol_headers(headers: dict) -> dict:
    """从子协议头里取出 token、device-id、client-id

    取出来的值与请求头形态保持一致（authorization 带 Bearer 前缀），
    这样下游不用关心凭证到底是从哪来的。
    """
    values = {}
    for item in headers.get("sec-websocket-protocol", "").split(","):
        item = item.strip()
        for prefix, key in WS_SUBPROTOCOL_FIELDS:
            if item.startswith(prefix) and len(item) > len(prefix):
                value = item[len(prefix) :]
                values[key] = f"Bearer {value}" if key == "authorization" else value
    return values


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging(config)
        self.config_lock = asyncio.Lock()
        modules = initialize_modules(
            self.logger,
            self.config,
            "VAD" in self.config["selected_module"],
            "ASR" in self.config["selected_module"],
            "LLM" in self.config["selected_module"],
            False,
            "Memory" in self.config["selected_module"],
            "Intent" in self.config["selected_module"],
        )
        self._vad = modules["vad"] if "vad" in modules else None
        self._asr = modules["asr"] if "asr" in modules else None
        self._llm = modules["llm"] if "llm" in modules else None
        self._intent = modules["intent"] if "intent" in modules else None
        self._memory = modules["memory"] if "memory" in modules else None

        self._load_auth_config(self.config)

    def _load_auth_config(self, config: dict):
        """从配置加载认证相关属性，改配置后可重复调用"""
        auth_config = config["server"].get("auth", {})
        self.auth_enable = auth_config.get("enabled", False)
        # 设备白名单：命中白名单只影响 token 的校验时长，不再跳过校验本身
        self.allowed_devices = set(auth_config.get("allowed_devices", []))
        # 白名单设备的 token 有效期，默认与普通设备一致，不因白名单放宽
        self.allowed_expire_seconds = auth_config.get(
            "allowed_devices_expire_seconds", None
        )
        secret_key = config["server"]["auth_key"]
        expire_seconds = auth_config.get("expire_seconds", None)
        issued_after = auth_config.get("issued_after", 0)
        self.auth = AuthManager(
            secret_key=secret_key,
            expire_seconds=expire_seconds,
            issued_after=issued_after,
        )

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("port", 8000))

        async with websockets.serve(
            self._handle_connection,
            host,
            port,
            process_request=self._http_response,
            select_subprotocol=self._select_subprotocol,
            ping_interval=None,
        ):
            await asyncio.Future()

    def _select_subprotocol(self, connection, subprotocols):
        """客户端按约定发了子协议就回显 xiaozhi，否则不选，回显会被浏览器拒掉"""
        return WS_SUBPROTOCOL if WS_SUBPROTOCOL in subprotocols else None

    def _connection_headers(self, websocket: websockets.ServerConnection) -> dict:
        """合并请求头与子协议头

        请求头优先，两者都不从 URL 查询串取：查询串会原样落进反代访问日志，
        设备标识和 token 都不该出现在那里。
        """
        headers = dict(websocket.request.headers)
        for key, value in _parse_subprotocol_headers(headers).items():
            if not headers.get(key):
                headers[key] = value
        return headers

    async def _handle_connection(self, websocket: websockets.ServerConnection):
        headers = self._connection_headers(websocket)
        if headers.get("device-id", None) is None:
            await websocket.send("端口正常，如需测试连接，请启动digital-human测试")
            await websocket.close()
            return

        """处理新连接，每次创建独立的ConnectionHandler"""
        # 先认证，后建立连接
        try:
            await self._handle_auth(websocket)
        except AuthenticationError:
            await websocket.send("认证失败")
            await websocket.close()
            return
        # 创建ConnectionHandler时传入当前server实例
        handler = ConnectionHandler(
            self.config,
            self._vad,
            self._asr,
            self._llm,
            self._memory,
            self._intent,
            self,  # 传入server实例
        )
        try:
            await handler.handle_connection(websocket)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"处理连接时出错: {e}")
        finally:
            # 强制关闭连接（如果还没有关闭的话）
            try:
                # 安全地检查WebSocket状态并关闭
                if hasattr(websocket, "closed") and not websocket.closed:
                    await websocket.close()
                elif hasattr(websocket, "state") and websocket.state.name != "CLOSED":
                    await websocket.close()
                else:
                    # 如果没有closed属性，直接尝试关闭
                    await websocket.close()
            except Exception as close_error:
                self.logger.bind(tag=TAG).error(
                    f"服务器端强制关闭连接时出错: {close_error}"
                )

    async def _http_response(self, websocket, request_headers):
        # 检查是否为 WebSocket 升级请求
        if request_headers.headers.get("connection", "").lower() == "upgrade":
            # 如果是 WebSocket 请求，返回 None 允许握手继续
            return None
        else:
            # 如果是普通 HTTP 请求，返回 "server is running"
            return websocket.respond(200, "Server is running\n")

    async def update_config(self) -> bool:
        """更新服务器配置并重新初始化组件

        Returns:
            bool: 更新是否成功
        """
        try:
            async with self.config_lock:
                # 重新获取配置（使用异步版本）
                new_config = await get_config_from_api_async(self.config)
                if new_config is None:
                    self.logger.bind(tag=TAG).error("获取新配置失败")
                    return False
                self.logger.bind(tag=TAG).info(f"获取新配置成功")
                # 检查 VAD 和 ASR 类型是否需要更新
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)
                self.logger.bind(tag=TAG).info(
                    f"检查VAD和ASR类型是否需要更新: {update_vad} {update_asr}"
                )
                # 更新配置
                self.config = new_config
                # 认证属性跟随配置刷新，避免改配置后不生效
                self._load_auth_config(new_config)
                # 重新初始化组件
                modules = initialize_modules(
                    self.logger,
                    new_config,
                    update_vad,
                    update_asr,
                    "LLM" in new_config["selected_module"],
                    False,
                    "Memory" in new_config["selected_module"],
                    "Intent" in new_config["selected_module"],
                )

                # 更新组件实例
                if "vad" in modules:
                    self._vad = modules["vad"]
                if "asr" in modules:
                    self._asr = modules["asr"]
                if "llm" in modules:
                    self._llm = modules["llm"]
                if "intent" in modules:
                    self._intent = modules["intent"]
                if "memory" in modules:
                    self._memory = modules["memory"]
                self.logger.bind(tag=TAG).info(f"更新配置任务执行完毕")
                return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"更新服务器配置失败: {str(e)}")
            return False

    async def _handle_auth(self, websocket: websockets.ServerConnection):
        # 先认证，后建立连接
        if self.auth_enable:
            headers = self._connection_headers(websocket)
            device_id = headers.get("device-id", None)
            client_id = headers.get("client-id", None)
            token = headers.get("authorization", "")
            if token.startswith("Bearer "):
                token = token[7:]  # 移除'Bearer '前缀
            else:
                raise AuthenticationError("Missing or invalid Authorization header")
            # 白名单设备只延长 token 有效期，仍然校验 token
            expire_seconds = None
            if self.allowed_devices and device_id in self.allowed_devices:
                expire_seconds = self.allowed_expire_seconds
            # 进行认证
            auth_success = self.auth.verify_token(
                token,
                client_id=client_id,
                username=device_id,
                expire_seconds=expire_seconds,
            )
            if not auth_success:
                raise AuthenticationError("Invalid token")
