import json
import time
import asyncio
from aiohttp import web
from config.logger import setup_logging
from core.connection import ConnectionHandler
from core.utils.util import get_local_ip, initialize_modules

TAG = __name__


class SimpleOtaServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()

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
        port = int(server_config.get("ota_port"))

        if port:
            app = web.Application()
            # 添加路由
            app.add_routes(
                [
                    web.get("/xiaozhi/ota/", self._handle_ota_get_request),
                    web.post("/xiaozhi/ota/", self._handle_ota_request),
                    web.options("/xiaozhi/ota/", self._handle_ota_request),
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

    async def _handle_ota_request(self, request):
        """处理 /xiaozhi/ota/ 的 POST 请求"""
        try:
            data = await request.text()
            self.logger.bind(tag=TAG).debug(f"OTA请求方法: {request.method}")
            self.logger.bind(tag=TAG).debug(f"OTA请求头: {request.headers}")
            self.logger.bind(tag=TAG).debug(f"OTA请求数据: {data}")

            device_id = request.headers.get("device-id", "")
            if device_id:
                self.logger.bind(tag=TAG).info(f"OTA请求设备ID: {device_id}")
            else:
                raise Exception("OTA请求设备ID为空")

            data_json = json.loads(data)

            server_config = self.config["server"]
            host = server_config.get("ip", "0.0.0.0")
            port = int(server_config.get("port", 8000))
            local_ip = get_local_ip()

            # OTA基础信息
            return_json = {
                "server_time": {
                    "timestamp": int(round(time.time() * 1000)),
                    "timezone_offset": server_config.get("timezone_offset", 8) * 60,
                },
                "firmware": {
                    "version": data_json["application"].get("version", "1.0.0"),
                    "url": "",
                },
                "websocket": {
                    "url": self._get_websocket_url(local_ip, port),
                },
            }
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"OTA请求异常: {e}")
            return_json = {"success": False, "message": "request error."}
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            # 添加header，允许跨域访问
            response.headers["Access-Control-Allow-Headers"] = (
                "client-id, content-type, device-id"
            )
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response

    async def _handle_ota_get_request(self, request):
        """处理 /xiaozhi/ota/ 的 GET 请求"""
        try:
            server_config = self.config["server"]
            local_ip = get_local_ip()
            port = int(server_config.get("port", 8000))
            websocket_url = self._get_websocket_url(local_ip, port)
            message = f"OTA接口运行正常，向设备发送的websocket地址是：{websocket_url}"
            response = web.Response(text=message, content_type="text/plain")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"OTA GET请求异常: {e}")
            response = web.Response(text="OTA接口异常", content_type="text/plain")
        finally:
            # 添加header，允许跨域访问
            response.headers["Access-Control-Allow-Headers"] = (
                "client-id, content-type, device-id"
            )
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
