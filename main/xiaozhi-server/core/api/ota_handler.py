import json
import time
from aiohttp import web
from core.utils.util import get_local_ip
from core.api.base_handler import BaseHandler

TAG = __name__


class OTAHandler(BaseHandler):
    def __init__(self, config: dict):
        super().__init__(config)

    def _get_websocket_url(self, local_ip: str, port: int) -> str:
        """获取websocket地址

        Args:
            local_ip: 本地IP地址
            port: 端口号

        Returns:
            str: websocket地址
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket", "")

        if "你的" not in websocket_config:
            return websocket_config
        else:
            return f"ws://{local_ip}:{port}/xiaozhi/v1/"

    async def handle_post(self, request):
        """处理 OTA POST 请求"""
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
            port = int(server_config.get("port", 8000))
            local_ip = get_local_ip()

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
            
            # Add MQTT gateway configuration if enabled
            mqtt_config = server_config.get("mqtt_gateway", {})
            if mqtt_config.get("enabled", False):
                return_json["mqtt_gateway"] = {
                    "broker": mqtt_config.get("broker", local_ip),
                    "port": mqtt_config.get("port", 1883),
                    "udp_port": mqtt_config.get("udp_port", 8884)
                }
                
                # Also add MQTT credentials section for client authentication
                import base64
                import hmac
                import hashlib
                
                client_id = f"GID_test@@@{device_id}@@@{data_json.get('client_id', 'default-client')}"
                
                # Create username (base64 encoded JSON) - must match client format
                username_data = {"ip": "192.168.1.100"}  # Placeholder IP
                username = base64.b64encode(json.dumps(username_data).encode()).decode()
                
                # Generate password using HMAC (must match gateway's signature key)
                secret_key = "test-signature-key-12345"  # Must match MQTT_SIGNATURE_KEY in gateway's .env
                content = f"{client_id}|{username}"
                password = base64.b64encode(hmac.new(secret_key.encode(), content.encode(), hashlib.sha256).digest()).decode()
                
                return_json["mqtt"] = {
                    "client_id": client_id,
                    "username": username,
                    "password": password
                }
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except Exception as e:
            return_json = {"success": False, "message": "request error."}
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            self._add_cors_headers(response)
            return response

    async def handle_get(self, request):
        """处理 OTA GET 请求"""
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
            self._add_cors_headers(response)
            return response
