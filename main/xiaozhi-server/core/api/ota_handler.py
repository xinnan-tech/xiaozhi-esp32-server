import json
import time
import uuid
import base64
import hmac
import hashlib
import os
import aiohttp
from aiohttp import web
from core.utils.util import get_local_ip
from core.api.base_handler import BaseHandler

# Try to load environment variables if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TAG = __name__


class OTAHandler(BaseHandler):
    def __init__(self, config: dict):
        super().__init__(config)
        # Load MQTT signature key from environment or config
        self.mqtt_signature_key = os.getenv(
            'MQTT_SIGNATURE_KEY', 'test-signature-key-12345')

    def _get_websocket_url(self, local_ip: str, port: int) -> str:
        """Get websocket address

        Args:
            local_ip: Local IP address
            port: Port number

        Returns:
            str: websocket address
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket", "")
        
        # Debug logging
        print(f"[OTA DEBUG] server_config websocket value: {websocket_config}")
        print(f"[OTA DEBUG] Full server config: {server_config}")

        if not websocket_config or "你的" in websocket_config:
            print(f"[OTA DEBUG] Using default websocket URL")
            return f"ws://{local_ip}:{port}/toy/v1/"
        else:
            print(f"[OTA DEBUG] Using configured websocket URL: {websocket_config}")
            return websocket_config

    def _generate_mqtt_credentials(self, device_id: str, client_ip: str) -> dict:
        """Generate MQTT credentials

        Args:
            device_id: Device ID (MAC address format)
            client_ip: Client IP address

        Returns:
            dict: MQTT credential information
        """
        # Convert MAC address format (remove colons, use underscores)
        mac_address = device_id.replace(":", "_")

        # Generate UUID for this session
        client_uuid = str(uuid.uuid4())

        # Create client ID in format: GID_test@@@mac_address@@@uuid
        group_id = "GID_test"
        client_id = f"{group_id}@@@{mac_address}@@@{client_uuid}"

        # Create user data and encode as base64 JSON
        user_data = {"ip": client_ip}
        username = base64.b64encode(json.dumps(user_data).encode()).decode()

        # Generate password signature
        content = f"{client_id}|{username}"
        password = base64.b64encode(
            hmac.new(self.mqtt_signature_key.encode(),
                     content.encode(), hashlib.sha256).digest()
        ).decode()

        return {
            "client_id": client_id,
            "username": username,
            "password": password
        }

    async def handle_post(self, request):
        """Handle OTA POST request"""
        try:
            data = await request.text()
            self.logger.bind(tag=TAG).debug(
                f"OTA request method: {request.method}")
            self.logger.bind(tag=TAG).debug(
                f"OTA request headers: {request.headers}")
            self.logger.bind(tag=TAG).debug(f"OTA request data: {data}")

            device_id = request.headers.get("device-id", "")
            if device_id:
                self.logger.bind(tag=TAG).info(
                    f"OTA request device ID: {device_id}")
            else:
                raise Exception("OTA request device ID is empty")

            data_json = json.loads(data)

            # Get client IP address
            client_ip = request.remote
            if request.headers.get('X-Forwarded-For'):
                client_ip = request.headers.get(
                    'X-Forwarded-For').split(',')[0].strip()
            elif request.headers.get('X-Real-IP'):
                client_ip = request.headers.get('X-Real-IP')

            server_config = self.config["server"]
            port = int(server_config.get("port", 8000))
            local_ip = get_local_ip()

            # Get MQTT gateway configuration if available
            mqtt_config = server_config.get("mqtt_gateway", {})
            mqtt_enabled = mqtt_config.get("enabled", False)
            mqtt_broker = mqtt_config.get("broker", local_ip)
            mqtt_port = mqtt_config.get("port", 1883)
            udp_port = mqtt_config.get("udp_port", 8884)

            # Generate MQTT credentials if MQTT is enabled
            mqtt_credentials = None
            if mqtt_enabled:
                mqtt_credentials = self._generate_mqtt_credentials(
                    device_id, client_ip)

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

            # Add MQTT credentials in the new format if enabled
            if mqtt_enabled and mqtt_credentials:
                return_json["mqtt"] = {
                    "endpoint": f"{mqtt_broker}:{mqtt_port}",
                    "client_id": mqtt_credentials["client_id"],
                    "username": mqtt_credentials["username"],
                    "password": mqtt_credentials["password"],
                    "publish_topic": "device-server",
                    "subscribe_topic": "null"
                }
            else:
                # Keep backward compatibility - include old format
                return_json.update({
                    "server": {
                        "ip": local_ip,
                        "port": port,
                        "http_port": server_config.get("http_port", 8003),
                    },
                    "mqtt_gateway": {
                        "enabled": mqtt_enabled,
                        "broker": mqtt_broker,
                        "port": mqtt_port,
                        "udp_port": udp_port,
                    },
                    "audio_params": {
                        "format": "opus",
                        "sample_rate": 16000,
                        "channels": 1,
                        "frame_duration": 60
                    }
                })

            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"OTA POST request exception: {e}")
            return_json = {"success": False, "message": "request error."}
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            self._add_cors_headers(response)
            return response

    async def handle_get(self, request):
        """Handle OTA GET request"""
        try:
            server_config = self.config["server"]
            local_ip = get_local_ip()
            port = int(server_config.get("port", 8000))
            http_port = server_config.get("http_port", 8003)
            websocket_url = self._get_websocket_url(local_ip, port)

            # Get MQTT gateway configuration
            mqtt_config = server_config.get("mqtt_gateway", {})
            mqtt_enabled = mqtt_config.get("enabled", False)
            mqtt_broker = mqtt_config.get("broker", local_ip)
            mqtt_port = mqtt_config.get("port", 1883)
            udp_port = mqtt_config.get("udp_port", 8884)

            message = f"""OTA interface running normally
Server configuration information:
- WebSocket address: {websocket_url}
- HTTP port: {http_port}
- WebSocket port: {port}
- MQTT gateway: {'Enabled' if mqtt_enabled else 'Disabled'}
- MQTT broker: {mqtt_broker}:{mqtt_port}
- UDP port: {udp_port}
- Server IP: {local_ip}"""

            response = web.Response(
                text=message, content_type="text/plain; charset=utf-8")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"OTA GET request exception: {e}")
            response = web.Response(
                text="OTA interface exception", content_type="text/plain")
        finally:
            self._add_cors_headers(response)
            return response
