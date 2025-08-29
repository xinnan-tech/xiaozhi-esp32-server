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
        """Get websocket address

        Args:
            local_ip: Local IP address
            port: Port number

        Returns:
            str: websocket address
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket")
        if websocket_config and "you" not in websocket_config:
            return websocket_config
        else:
            return f"ws://{local_ip}:{port}/toy/v1/"

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("http_port", 8003))

        if port:
            try:
                self.logger.bind(tag=TAG).info(
                    f"Starting HTTP server on {host}:{port}")
                app = web.Application()

                read_config_from_api = server_config.get(
                    "read_config_from_api", False)
                self.logger.bind(tag=TAG).info(
                    f"read_config_from_api: {read_config_from_api}")

                if not read_config_from_api:
                    # If smart control panel is not enabled, just running single module, need to add simple OTA interface for delivering websocket interface
                    self.logger.bind(tag=TAG).info("Adding OTA routes")
                    app.add_routes([
                        web.get("/toy/ota/", self.ota_handler.handle_get),
                        web.post("/toy/ota/",
                                 self.ota_handler.handle_post),
                        web.options("/toy/ota/",
                                    self.ota_handler.handle_post),
                    ])

                # Add routes
                self.logger.bind(tag=TAG).info("Adding vision routes")
                app.add_routes([
                    web.get("/mcp/vision/explain",
                            self.vision_handler.handle_get),
                    web.post("/mcp/vision/explain",
                             self.vision_handler.handle_post),
                    web.options("/mcp/vision/explain",
                                self.vision_handler.handle_post),
                ])

                # Run service
                self.logger.bind(tag=TAG).info("Setting up HTTP server runner")
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, host, port)
                await site.start()

                self.logger.bind(tag=TAG).info(
                    f"HTTP server started successfully on {host}:{port}")

                # Keep service running
                while True:
                    await asyncio.sleep(3600)  # Check every hour

            except Exception as e:
                self.logger.bind(tag=TAG).error(
                    f"Failed to start HTTP server: {e}")
                raise
