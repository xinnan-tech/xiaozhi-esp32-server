from aiohttp import web
from config.logger import setup_logging


class BaseHandler:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()

    def _resolve_cors_origin(self, origin: str | None) -> str | None:
        """回显允许的 Origin，取不到或不在名单里时不放 CORS 头"""
        if not origin:
            return None
        cors = self.config.get("server", {}).get("cors", {}) or {}
        allowed = cors.get("allowed_origins", ["*"]) or ["*"]
        if "*" in allowed:
            return origin
        return origin if origin in allowed else None

    def _add_cors_headers(self, response, request=None):
        """添加CORS头信息"""
        response.headers["Access-Control-Allow-Headers"] = (
            "client-id, content-type, device-id, authorization"
        )
        origin = self._resolve_cors_origin(
            request.headers.get("Origin") if request is not None else None
        )
        if origin:
            # 回显具体 Origin，配合 Allow-Credentials 才是浏览器规范允许的写法
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Vary"] = "Origin"

    async def handle_options(self, request):
        """处理OPTIONS请求，添加CORS头信息"""
        response = web.Response(body=b"", content_type="text/plain")
        self._add_cors_headers(response, request)
        # 添加允许的方法
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response
