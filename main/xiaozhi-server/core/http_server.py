import asyncio
from aiohttp import web
from config.logger import setup_logging
from core.api.native_mqtt_management_handler import (
    NativeMqttManagementHandler,
)
from core.api.ota_handler import OTAHandler
from core.api.vision_handler import VisionHandler

TAG = __name__


class SimpleHttpServer:
    def __init__(self, config: dict, management_owner=None):
        self.config = config
        self.management_owner = management_owner
        self.logger = setup_logging()
        self.ota_handler = OTAHandler(config)
        self.vision_handler = VisionHandler(config)
        self.native_mqtt_management_handler = (
            NativeMqttManagementHandler(config, management_owner)
            if management_owner is not None and self._native_mqtt_enabled()
            else None
        )
        self._started_event = asyncio.Event()
        self._stop_event = asyncio.Event()
        self._runner = None
        self._start_active = False
        self._cleanup_lock = asyncio.Lock()

    def _native_mqtt_enabled(self) -> bool:
        mqtt_config = self.config.get("mqtt_server", {})
        enabled_protocols = self.config.get("enabled_protocols", [])
        return (
            isinstance(mqtt_config, dict)
            and mqtt_config.get("enabled") is True
            and "mqtt" in enabled_protocols
        )

    async def wait_started(self, task: asyncio.Task, timeout: float = 10) -> None:
        """Wait until the HTTP listener is bound or surface startup failure."""
        event_waiter = asyncio.create_task(self._started_event.wait())
        try:
            done, _ = await asyncio.wait(
                {task, event_waiter},
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if self._started_event.is_set():
                if task.done():
                    await task
                return
            if task in done:
                await task
                raise RuntimeError("HTTP服务器在就绪前退出")
            raise TimeoutError("等待HTTP服务器启动超时")
        finally:
            if not event_waiter.done():
                event_waiter.cancel()
                await asyncio.gather(event_waiter, return_exceptions=True)

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
        runner = None
        self._start_active = True
        try:
            self._started_event.clear()
            self._stop_event.clear()
            server_config = self.config["server"]
            read_config_from_api = self.config.get("read_config_from_api", False)
            host = server_config.get("ip", "0.0.0.0")
            port = int(server_config.get("http_port", 8003))

            if port:
                mqtt_config = self.config.get("mqtt_server", {})
                client_max_size = max(
                    1024,
                    int(
                        mqtt_config.get(
                            "manager_max_request_size", 64 * 1024
                        )
                        or 64 * 1024
                    ),
                )
                app = web.Application(client_max_size=client_max_size)

                if not read_config_from_api:
                    # 如果没有开启智控台，只是单模块运行，就需要再添加简单OTA接口，用于下发websocket接口
                    app.add_routes(
                        [
                            web.get("/xiaozhi/ota/", self.ota_handler.handle_get),
                            web.post("/xiaozhi/ota/", self.ota_handler.handle_post),
                            web.options(
                                "/xiaozhi/ota/", self.ota_handler.handle_options
                            ),
                            # 下载接口，仅提供 data/bin/*.bin 下载
                            web.get(
                                "/xiaozhi/ota/download/{filename}",
                                self.ota_handler.handle_download,
                            ),
                            web.options(
                                "/xiaozhi/ota/download/{filename}",
                                self.ota_handler.handle_options,
                            ),
                        ]
                    )
                # 添加路由
                app.add_routes(
                    [
                        web.get("/mcp/vision/explain", self.vision_handler.handle_get),
                        web.post(
                            "/mcp/vision/explain", self.vision_handler.handle_post
                        ),
                        web.options(
                            "/mcp/vision/explain", self.vision_handler.handle_options
                        ),
                    ]
                )
                if self.native_mqtt_management_handler is not None:
                    app.add_routes(
                        [
                            web.post(
                                "/api/devices/status",
                                self.native_mqtt_management_handler.handle_device_status,
                            ),
                            web.post(
                                "/api/commands/{client_id}",
                                self.native_mqtt_management_handler.handle_command,
                            ),
                            web.post(
                                "/api/call/request",
                                self.native_mqtt_management_handler.handle_call_request,
                            ),
                            web.post(
                                "/api/call/accept",
                                self.native_mqtt_management_handler.handle_call_accept,
                            ),
                        ]
                    )

                # 运行服务
                runner = web.AppRunner(app)
                self._runner = runner
                await runner.setup()
                site = web.TCPSite(runner, host, port)
                await site.start()
            self._started_event.set()
            await self._stop_event.wait()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"HTTP服务器启动失败: {e}")
            import traceback

            self.logger.bind(tag=TAG).error(f"错误堆栈: {traceback.format_exc()}")
            raise
        finally:
            self._started_event.clear()
            try:
                if runner is not None:
                    await self._cleanup_runner()
            finally:
                self._start_active = False

    async def _cleanup_runner(self):
        """Cleanup the owned runner and retain it when cleanup must be retried."""
        async with self._cleanup_lock:
            runner = self._runner
            if runner is None:
                return
            await runner.cleanup()
            self._runner = None

    async def stop(self):
        """Stop the HTTP loop and retry cleanup left by a failed start task."""
        self._stop_event.set()
        if not self._start_active:
            await self._cleanup_runner()
