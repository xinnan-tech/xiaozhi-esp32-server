import copy
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from aiohttp import web

from config.logger import setup_logging
from core.providers.tools.device_mcp import call_mcp_tool
from core.utils.mqtt_auth import normalize_signature_key
from core.utils.util import sanitize_tool_name

TAG = __name__


class NativeMqttManagementHandler:
    def __init__(self, config: Dict[str, Any], management_owner: Any):
        self.config = config
        self.management_owner = management_owner
        self.logger = setup_logging()
        mqtt_config = config.get("mqtt_server", {})
        server_config = config.get("server", {})
        self.signature_key = normalize_signature_key(
            mqtt_config.get("manager_api_secret")
            or mqtt_config.get("signature_key")
            or server_config.get("mqtt_signature_key")
        )
        self.command_timeout = max(
            0.1, float(mqtt_config.get("manager_command_timeout", 5) or 5)
        )
        self.max_status_ids = max(
            1, int(mqtt_config.get("manager_max_status_ids", 1000) or 1000)
        )

    @staticmethod
    def generate_daily_tokens(
        signature_key: str, now: Optional[datetime] = None
    ) -> set[str]:
        normalized = normalize_signature_key(signature_key)
        if not normalized:
            return set()
        current = now or datetime.now(timezone.utc)
        utc_date = current.astimezone(timezone.utc).date()
        return {
            hashlib.sha256(
                f"{utc_date + timedelta(days=offset)}{normalized}".encode(
                    "utf-8"
                )
            ).hexdigest()
            for offset in (-1, 0, 1)
        }

    def _is_authorized(self, authorization: str) -> bool:
        if not self.signature_key:
            return False
        if not authorization or not authorization.startswith("Bearer "):
            return False
        provided = authorization[len("Bearer ") :].strip()
        return any(
            hmac.compare_digest(provided, expected)
            for expected in self.generate_daily_tokens(self.signature_key)
        )

    def _authorize(self, request) -> Optional[web.Response]:
        if not self.signature_key:
            return self._error(
                503,
                "Native MQTT管理API未配置签名密钥",
                "MANAGEMENT_AUTH_NOT_CONFIGURED",
                False,
            )
        if not self._is_authorized(request.headers.get("Authorization", "")):
            return self._error(
                401, "无效的授权令牌", "UNAUTHORIZED", False
            )
        return None

    @staticmethod
    def _error(
        status: int,
        message: str,
        code: str,
        dispatch_attempted: bool,
    ) -> web.Response:
        return web.json_response(
            {
                "success": False,
                "error": message,
                "code": code,
                "dispatchAttempted": dispatch_attempted,
            },
            status=status,
        )

    async def _read_json_object(self, request) -> Optional[Dict[str, Any]]:
        try:
            body = await request.json()
        except Exception:
            return None
        return body if isinstance(body, dict) else None

    async def handle_device_status(self, request) -> web.Response:
        unauthorized = self._authorize(request)
        if unauthorized is not None:
            return unauthorized

        body = await self._read_json_object(request)
        client_ids = body.get("clientIds") if body else None
        if (
            not isinstance(client_ids, list)
            or not client_ids
            or len(client_ids) > self.max_status_ids
            or any(
                not isinstance(client_id, str) or not client_id
                for client_id in client_ids
            )
        ):
            return self._error(
                400,
                "clientIds必须是非空字符串数组且未超过数量限制",
                "INVALID_CLIENT_IDS",
                False,
            )

        get_status = getattr(
            self.management_owner, "get_native_mqtt_status", None
        )
        if not callable(get_status):
            return self._error(
                503,
                "Native MQTT管理服务未就绪",
                "MANAGEMENT_NOT_READY",
                False,
            )
        return web.json_response(await get_status(client_ids))

    async def handle_command(self, request) -> web.Response:
        unauthorized = self._authorize(request)
        if unauthorized is not None:
            return unauthorized

        body = await self._read_json_object(request)
        payload = (
            body.get("payload")
            if body and body.get("type") == "mcp"
            else None
        )
        if not isinstance(payload, dict):
            return self._error(
                400, "指令类型无效", "INVALID_COMMAND", False
            )

        resolver = getattr(
            self.management_owner, "resolve_native_mqtt_connection", None
        )
        if not callable(resolver):
            return self._error(
                503,
                "Native MQTT管理服务未就绪",
                "MANAGEMENT_NOT_READY",
                False,
            )

        connection = await resolver(request.match_info.get("client_id", ""))
        if connection is None:
            return self._error(
                404, "设备未连接", "DEVICE_OFFLINE", False
            )

        method = payload.get("method")
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            return self._error(
                400, "MCP参数格式无效", "INVALID_MCP_PARAMS", False
            )
        if method == "tools/list":
            return await self._list_tools(connection.context)
        if method == "tools/call":
            return await self._call_tool(connection.context, params)
        return self._error(
            422, "不支持的MCP方法", "UNSUPPORTED_MCP_METHOD", False
        )

    async def handle_call_request(self, request) -> web.Response:
        unauthorized = self._authorize(request)
        if unauthorized is not None:
            return unauthorized

        body = await self._read_json_object(request)
        caller_mac = body.get("caller_mac") if body else None
        target_mac = body.get("target_mac") if body else None
        caller_nickname = body.get("caller_nickname", "") if body else ""
        if (
            not isinstance(caller_mac, str)
            or not caller_mac.strip()
            or not isinstance(target_mac, str)
            or not target_mac.strip()
            or not isinstance(caller_nickname, str)
        ):
            return web.json_response(
                {
                    "status": "error",
                    "message": "缺少必要参数: caller_mac, target_mac",
                },
                status=400,
            )

        request_call = getattr(
            self.management_owner, "request_native_mqtt_call", None
        )
        if not callable(request_call):
            return web.json_response(
                {"status": "error", "message": "Native MQTT呼叫服务未就绪"},
                status=503,
            )
        result = await request_call(
            caller_mac, target_mac, caller_nickname
        )
        return web.json_response(result)

    async def handle_call_accept(self, request) -> web.Response:
        unauthorized = self._authorize(request)
        if unauthorized is not None:
            return unauthorized

        body = await self._read_json_object(request)
        device_id = body.get("mac") if body else None
        if not isinstance(device_id, str) or not device_id.strip():
            return web.json_response(
                {"status": "error", "message": "缺少必要参数: mac"},
                status=400,
            )

        accept_call = getattr(
            self.management_owner, "accept_native_mqtt_call", None
        )
        if not callable(accept_call):
            return web.json_response(
                {"status": "error", "message": "Native MQTT呼叫服务未就绪"},
                status=503,
            )
        return web.json_response(await accept_call(device_id))

    async def _list_tools(self, context) -> web.Response:
        mcp_client = getattr(context, "mcp_client", None)
        if mcp_client is None or not await mcp_client.is_ready():
            return self._error(
                503,
                "设备MCP尚未准备就绪",
                "MCP_NOT_READY",
                False,
            )

        async with mcp_client.lock:
            tools = [
                copy.deepcopy(tool)
                for tool in mcp_client.tools.values()
            ]
        return web.json_response(
            {"success": True, "data": {"tools": tools}}
        )

    async def _call_tool(self, context, params: Dict[str, Any]) -> web.Response:
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(tool_name, str) or not tool_name:
            return self._error(
                422, "工具名称不能为空", "INVALID_TOOL_NAME", False
            )
        if not isinstance(arguments, dict):
            return self._error(
                422, "工具参数必须是对象", "INVALID_TOOL_ARGUMENTS", False
            )

        mcp_client = getattr(context, "mcp_client", None)
        if mcp_client is None or not await mcp_client.is_ready():
            return self._error(
                503,
                "设备MCP尚未准备就绪",
                "MCP_NOT_READY",
                False,
            )

        sanitized_name = sanitize_tool_name(tool_name)
        if not mcp_client.has_tool(sanitized_name):
            return self._error(
                422, "设备不存在该工具", "TOOL_NOT_FOUND", False
            )

        try:
            result = await call_mcp_tool(
                context,
                mcp_client,
                sanitized_name,
                arguments,
                timeout=self.command_timeout,
                return_raw=True,
            )
        except TimeoutError:
            return self._error(
                504, "工具调用请求超时", "COMMAND_TIMEOUT", True
            )
        except ConnectionError:
            return self._error(
                503, "设备连接已关闭", "DEVICE_DISCONNECTED", True
            )
        except ValueError as error:
            return self._error(422, str(error), "INVALID_TOOL_CALL", False)
        except Exception as error:
            self.logger.bind(tag=TAG).warning(
                "Native MQTT设备工具调用失败: {}", error
            )
            return self._error(
                502, str(error), "TOOL_CALL_FAILED", True
            )

        data = (
            result
            if isinstance(result, dict)
            else {"content": [{"type": "text", "text": str(result)}]}
        )
        return web.json_response({"success": True, "data": data})
