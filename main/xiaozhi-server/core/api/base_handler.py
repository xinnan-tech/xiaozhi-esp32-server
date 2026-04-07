from aiohttp import web
from config.logger import setup_logging


class BaseHandler:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()

    def _add_cors_headers(self, response, request=None):
        """添加CORS头信息"""
        response.headers["Access-Control-Allow-Headers"] = (
            "client-id, content-type, device-id, authorization"
        )

        trusted_origins = self.config.get("trusted_origins") or self.config.get(
            "cors_allowed_origins"
        ) or []
        if isinstance(trusted_origins, str):
            trusted_origins = [trusted_origins]

        origin = request.headers.get("Origin") if request else None
        if origin in trusted_origins:
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
