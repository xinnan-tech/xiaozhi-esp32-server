"""本机设备工具接口：让同一台机器上的外部程序（自动化脚本、其他智能体）调用已连接设备上报的 MCP 工具。

默认关闭，需在配置里打开 server.device_tool_api: true；只接受来自 127.0.0.1 / ::1 的请求。

  GET  /xiaozhi/device/tools   列出当前已连接的设备、其上报的工具名、工具列表是否就绪
  POST /xiaozhi/device/call    {"tool": 工具名, "arguments": {...}, "device_id": 可省（仅一台在线时）, "timeout": 秒}

注意：设备只有在建立 WebSocket 会话后才会出现在列表中（例如唤醒或按键开始对话之后）。
"""

import json
import time

from aiohttp import web

from config.logger import setup_logging
from core.api.base_handler import BaseHandler

TAG = __name__

# 当前在线的 ConnectionHandler；device_id 在握手后才设置，所以查询时再读取
_active_connections = set()


def register_connection(handler):
    _active_connections.add(handler)


def unregister_connection(handler):
    _active_connections.discard(handler)


def _online():
    return {
        h.device_id: h
        for h in list(_active_connections)
        if getattr(h, "device_id", None)
    }


class DeviceToolHandler(BaseHandler):
    def __init__(self, config: dict):
        super().__init__(config)
        self.logger = setup_logging()

    @staticmethod
    def _is_local(request) -> bool:
        return request.remote in ("127.0.0.1", "::1")

    def _json(self, data, status=200):
        response = web.json_response(data, status=status, dumps=lambda o: json.dumps(o, ensure_ascii=False))
        self._add_cors_headers(response)
        return response

    async def handle_list(self, request):
        if not self._is_local(request):
            return self._json({"error": "only local requests are allowed"}, status=403)
        result = []
        for device_id, handler in _online().items():
            client = getattr(handler, "mcp_client", None)
            ready = bool(client) and await client.is_ready()
            result.append(
                {
                    "device_id": device_id,
                    "tools": sorted(client.tools) if client else [],
                    "ready": ready,
                }
            )
        return self._json(result)

    async def handle_call(self, request):
        if not self._is_local(request):
            return self._json({"error": "only local requests are allowed"}, status=403)
        try:
            body = await request.json()
        except Exception:
            return self._json({"error": "request body must be JSON"}, status=400)

        online = _online()
        device_id = body.get("device_id") or (next(iter(online)) if len(online) == 1 else None)
        handler = online.get(device_id)
        if not handler:
            message = "device not connected" if not online else "more than one device online, device_id is required"
            return self._json({"error": message, "online": list(online)}, status=404)

        client = getattr(handler, "mcp_client", None)
        if not client or not await client.is_ready():
            return self._json({"error": "device tool list is not ready yet"}, status=503)

        from core.providers.tools.device_mcp.mcp_handler import call_mcp_tool

        started = time.time()
        try:
            result = await call_mcp_tool(
                handler,
                client,
                body.get("tool", ""),
                json.dumps(body.get("arguments", {}), ensure_ascii=False),
                timeout=int(body.get("timeout", 15)),
            )
        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"本机设备工具调用失败: {e}")
            return self._json({"error": f"{type(e).__name__}: {e}", "device_id": device_id}, status=502)
        return self._json(
            {
                "device_id": device_id,
                "tool": body.get("tool"),
                "result": result,
                "seconds": round(time.time() - started, 2),
            }
        )
