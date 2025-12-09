import asyncio
from pathlib import Path
from aiohttp import web
from config.logger import setup_logging
from core.api.ota_handler import OTAHandler
from core.api.vision_handler import VisionHandler

TAG = __name__


class SimpleHttpServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.ota_handler = OTAHandler(config)
        self.vision_handler = VisionHandler(config)
        # assets.bin 存放目录（默认放在项目 assets_fw 下）
        base_dir = Path(__file__).resolve().parents[1]
        self.assets_dir = base_dir / "assets_fw"
        self.assets_file = self.assets_dir / "assets.bin"

    def _get_websocket_url(self, local_ip: str, port: int) -> str:
        """获取websocket地址

        Args:
            local_ip: 本地IP地址
            port: 端口号

        Returns:
            str: websocket地址
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket")

        if websocket_config and "你" not in websocket_config:
            return websocket_config
        else:
            return f"ws://{local_ip}:{port}/xiaozhi/v1/"

    async def start(self):
        server_config = self.config["server"]
        read_config_from_api = self.config.get("read_config_from_api", False)
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("http_port", 8003))

        if port:
            app = web.Application(middlewares=[self.cors_middleware])

            if not read_config_from_api:
                # 如果没有开启智控台，只是单模块运行，就需要再添加简单OTA接口，用于下发websocket接口
                app.add_routes(
                    [
                        web.get("/xiaozhi/ota/", self.ota_handler.handle_get),
                        web.post("/xiaozhi/ota/", self.ota_handler.handle_post),
                        web.options("/xiaozhi/ota/", self.ota_handler.handle_post),
                    ]
                )
            # 添加路由
            app.add_routes(
                [
                    web.get("/mcp/vision/explain", self.vision_handler.handle_get),
                    web.post("/mcp/vision/explain", self.vision_handler.handle_post),
                    web.options("/mcp/vision/explain", self.vision_handler.handle_post),
                    # assets.bin 下载/上传
                    web.get("/xiaozhi/trans/assets.bin", self.handle_assets_download),
                    web.post("/xiaozhi/trans/upload", self.handle_assets_upload),
                    web.options("/xiaozhi/trans/upload", self.handle_assets_upload),
                ]
            )

            # 运行服务
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()

            # 保持服务运行
            while True:
                await asyncio.sleep(3600)  # 每隔 1 小时检查一次

    @web.middleware
    async def cors_middleware(self, request, handler):
        """简单 CORS 处理，允许前端 8001 访问"""
        allowed_origin = f"http://{request.host.split(':')[0]}:8001"
        try:
            resp = await handler(request)
        except web.HTTPException as ex:
            resp = ex
        if isinstance(resp, web.StreamResponse):
            resp.headers["Access-Control-Allow-Origin"] = allowed_origin
            resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
            resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return resp

    async def handle_assets_download(self, request: web.Request) -> web.StreamResponse:
        """提供 assets.bin 下载"""
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        if not self.assets_file.exists():
            return web.Response(status=404, text="assets.bin not found")
        return web.FileResponse(path=self.assets_file)

    async def handle_assets_upload(self, request: web.Request) -> web.Response:
        """接收上传的 assets.bin 并保存到本地"""
        if request.method == "OPTIONS":
            return web.Response(status=200)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        # 每次上传前先删除旧的，确保是最新文件
        if self.assets_file.exists():
            try:
                self.assets_file.unlink()
            except Exception:
                # 忽略删除异常，继续后续写入
                pass
        reader = await request.multipart()
        field = await reader.next()
        if not field or field.name not in ("file", "asset", "upload"):
            return web.json_response({"success": False, "message": "missing file field"}, status=400)
        filename = field.filename or "assets.bin"
        data = await field.read(decode=True)
        try:
            self.assets_dir.mkdir(parents=True, exist_ok=True)
            with open(self.assets_file, "wb") as f:
                f.write(data)
        except Exception as e:
            return web.json_response({"success": False, "message": f"save failed: {e}"}, status=500)
        return web.json_response(
            {
                "success": True,
                "message": "uploaded",
                "filename": filename,
                "size": len(data),
                "path": str(self.assets_file),
            }
        )
