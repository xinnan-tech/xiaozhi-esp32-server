from aiohttp import web
from config.logger import setup_logging


class BaseHandler:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self._cors_wildcard_warned = False

    def _resolve_cors_origin(self, origin: str | None) -> str | None:
        """回显名单内的 Origin；其余情况不下发 CORS 头，由浏览器拦截

        这里刻意不支持通配：回显任意来源并带上 Allow-Credentials 会让任意网站
        都能带凭证读响应，而固定写 "*" 配 Allow-Credentials 属于浏览器明确
        拒绝的组合，反而挡得更严。宁可什么都不放，也不放宽。
        """
        if not origin:
            return None
        cors = self.config.get("server", {}).get("cors", {}) or {}
        allowed = cors.get("allowed_origins", []) or []
        if "*" in allowed and not self._cors_wildcard_warned:
            self._cors_wildcard_warned = True
            self.logger.bind(tag="BaseHandler").warning(
                "cors.allowed_origins 里的 * 不会放行任意来源，请填写具体来源"
            )
        return origin if origin in allowed else None

    def _add_cors_headers(self, response, request=None):
        """添加CORS头信息"""
        response.headers["Access-Control-Allow-Headers"] = (
            "client-id, content-type, device-id, authorization"
        )
        requested_origin = (
            request.headers.get("Origin") if request is not None else None
        )
        origin = self._resolve_cors_origin(requested_origin)
        if requested_origin:
            # 只要请求带了 Origin 就标 Vary，哪怕这次没放行，
            # 否则共享缓存会把带放行头的响应喂给别的来源
            response.headers["Vary"] = "Origin"
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"

    async def handle_options(self, request):
        """处理OPTIONS请求，添加CORS头信息"""
        response = web.Response(body=b"", content_type="text/plain")
        self._add_cors_headers(response, request)
        # 添加允许的方法
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response
