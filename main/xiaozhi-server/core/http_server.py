import asyncio
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
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("http_port", 8003))

        if port:
            try:
                self.logger.bind(tag=TAG).info(f"Starting HTTP server on {host}:{port}")
                app = web.Application()

                read_config_from_api = server_config.get("read_config_from_api", False)
                self.logger.bind(tag=TAG).info(f"read_config_from_api: {read_config_from_api}")

                if not read_config_from_api:
                    # 如果没有开启智控台，只是单模块运行，就需要再添加简单OTA接口，用于下发websocket接口
                    self.logger.bind(tag=TAG).info("Adding OTA routes")
                    app.add_routes(
                        [
                            web.get("/xiaozhi/ota/", self.ota_handler.handle_get),
                            web.post("/xiaozhi/ota/", self.ota_handler.handle_post),
                            web.options("/xiaozhi/ota/", self.ota_handler.handle_post),
                        ]
                    )
                # 添加路由
                self.logger.bind(tag=TAG).info("Adding vision routes")
                app.add_routes(
                    [
                        web.get("/mcp/vision/explain", self.vision_handler.handle_get),
                        web.post("/mcp/vision/explain", self.vision_handler.handle_post),
                        web.options("/mcp/vision/explain", self.vision_handler.handle_post),
                    ]
                )

                # 运行服务
                self.logger.bind(tag=TAG).info("Setting up HTTP server runner")
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, host, port)
                await site.start()
                self.logger.bind(tag=TAG).info(f"HTTP server started successfully on {host}:{port}")

                # 保持服务运行
                while True:
                    await asyncio.sleep(3600)  # 每隔 1 小时检查一次
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"Failed to start HTTP server: {e}")
                raise
