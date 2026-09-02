import asyncio
import logging

import websockets
from config.logger import setup_logging


class SuppressInvalidHandshakeFilter(logging.Filter):
    """Filter out invalid handshake error logs (e.g. HTTPS access to WS port)"""

    def filter(self, record):
        msg = record.getMessage()
        suppress_keywords = [
            "opening handshake failed",
            "did not receive a valid HTTP request",
            "connection closed while reading HTTP request",
            "line without CRLF",
        ]
        return not any(keyword in msg for keyword in suppress_keywords)


def _setup_websockets_logger():
    """Configure all websockets related loggers, filter invalid handshake errors"""
    filter_instance = SuppressInvalidHandshakeFilter()
    for logger_name in ["websockets", "websockets.server", "websockets.client"]:
        logger = logging.getLogger(logger_name)
        logger.addFilter(filter_instance)


_setup_websockets_logger()


from core.connection import ConnectionHandler
from config.config_loader import get_config_from_api_async
from core.auth import AuthManager, AuthenticationError
from core.utils.modules_initialize import initialize_modules
from core.utils.util import check_vad_update, check_asr_update

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.config_lock = asyncio.Lock()
        modules = initialize_modules(
            self.logger,
            self.config,
            "VAD" in self.config["selected_module"],
            "ASR" in self.config["selected_module"],
            "LLM" in self.config["selected_module"],
            "TTS" in self.config["selected_module"],
            "Memory" in self.config["selected_module"],
            "Intent" in self.config["selected_module"],
        )
        self._vad = modules["vad"] if "vad" in modules else None
        self._asr = modules["asr"] if "asr" in modules else None
        self._tts = modules["tts"] if "tts" in modules else None
        self._llm = modules["llm"] if "llm" in modules else None
        self._intent = modules["Intent"] if "Intent" in modules else None
        self._memory = modules["memory"] if "memory" in modules else None

        auth_config = self.config["server"].get("auth", {})
        self.auth_enable = auth_config.get("enabled", False)
        # Device whitelist
        self.allowed_devices = set(auth_config.get("allowed_devices", []))
        secret_key = self.config["server"]["auth_key"]
        expire_seconds = auth_config.get("expire_seconds", None)
        self.auth = AuthManager(secret_key=secret_key, expire_seconds=expire_seconds)

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("port", 8000))

        import ssl
        import os

        ssl_context = None
        ssl_cert = server_config.get("ssl_cert")
        ssl_key = server_config.get("ssl_key")

        if ssl_cert and ssl_key:
            if os.path.exists(ssl_cert) and os.path.exists(ssl_key):
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(certfile=ssl_cert, keyfile=ssl_key)
                self.logger.bind(tag=TAG).info(f"WSS (SSL) enabled using {ssl_cert}")
            else:
                self.logger.bind(tag=TAG).error(f"SSL cert/key files not found: {ssl_cert}, {ssl_key}")

        async with websockets.serve(
            self._handle_connection, 
            host, 
            port, 
            process_request=self._http_response,
            ssl=ssl_context
        ):
            await asyncio.Future()

    async def _handle_connection(self, websocket):
        headers = dict(websocket.request.headers)
        if headers.get("device-id", None) is None:
            # Try to get device-id from URL query parameters
            from urllib.parse import parse_qs, urlparse

            # Get path from WebSocket request
            request_path = websocket.request.path
            if not request_path:
                self.logger.bind(tag=TAG).error("Unable to get request path")
                await websocket.close()
                return
            parsed_url = urlparse(request_path)
            query_params = parse_qs(parsed_url.query)
            if "device-id" not in query_params:
#                await websocket.send("Port is working normally. To test connection, please use test_page.html")
                await websocket.send("The port is working. To test use... test_page.html")
                await websocket.close()
                return
            else:
                websocket.request.headers["device-id"] = query_params["device-id"][0]
            if "client-id" in query_params:
                websocket.request.headers["client-id"] = query_params["client-id"][0]
            if "authorization" in query_params:
                websocket.request.headers["authorization"] = query_params[
                    "authorization"
                ][0]

        """Handle new connection, create independent ConnectionHandler each time"""
        # Authenticate first, then establish connection
        try:
            await self._handle_auth(websocket)
        except AuthenticationError:
            await websocket.send("Authentication failed")
            await websocket.close()
            return
        # Pass current server instance when creating ConnectionHandler
        handler = ConnectionHandler(
            self.config,
            self._vad,
            self._asr,
            self._tts,
            self._llm,
            self._memory,
            self._intent,
            self,  # Pass server instance
        )
        try:
            await handler.handle_connection(websocket)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Error handling connection: {e}")
        finally:
            # Force close connection (if not already closed)
            try:
                # Safely check WebSocket state and close
                if hasattr(websocket, "closed") and not websocket.closed:
                    await websocket.close()
                elif hasattr(websocket, "state") and websocket.state.name != "CLOSED":
                    await websocket.close()
                else:
                    # If no closed attribute, try to close directly
                    await websocket.close()
            except Exception as close_error:
                self.logger.bind(tag=TAG).error(
                    f"Error during server forced connection close: {close_error}"
                )

    async def _http_response(self, websocket, request_headers):
        # Check if it is a WebSocket upgrade request
        if request_headers.headers.get("connection", "").lower() == "upgrade":
            # If it is a WebSocket request, return None to allow handshake to continue
            return None
        else:
            # If it is a normal HTTP request, return "server is running"
            return websocket.respond(200, "Server is running\n")

    async def update_config(self) -> bool:
        """Update server configuration and re-initialize components

        Returns:
            bool: Whether update was successful
        """
        try:
            async with self.config_lock:
                # Re-fetch auth (use async version)
                new_config = await get_config_from_api_async(self.config)
                if new_config is None:
                    self.logger.bind(tag=TAG).error("Failed to fetch new config")
                    return False
                self.logger.bind(tag=TAG).info(f"Fetch new config success")
                # Check if VAD and ASR types need update
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)
                self.logger.bind(tag=TAG).info(
                    f"Check if VAD and ASR types need update: {update_vad} {update_asr}"
                )
                # Update config
                self.config = new_config
                # Re-initialize components
                modules = initialize_modules(
                    self.logger,
                    new_config,
                    update_vad,
                    update_asr,
                    "LLM" in new_config["selected_module"],
                    False,
                    "Memory" in new_config["selected_module"],
                    "Intent" in new_config["selected_module"],
                )

                # Update component instances
                if "vad" in modules:
                    self._vad = modules["vad"]
                if "asr" in modules:
                    self._asr = modules["asr"]
                if "llm" in modules:
                    self._llm = modules["llm"]
                if "Intent" in modules:
                    self._intent = modules["Intent"]
                if "memory" in modules:
                    self._memory = modules["memory"]
                self.logger.bind(tag=TAG).info(f"Config update task completed")
                return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Failed to update server config: {str(e)}")
            return False

    async def _handle_auth(self, websocket):
        # Authenticate first, then establish connection
        if self.auth_enable:
            headers = dict(websocket.request.headers)
            device_id = headers.get("device-id", None)
            client_id = headers.get("client-id", None)
            if self.allowed_devices and device_id in self.allowed_devices:
                # If in allowable devices list, skip token check
                return
            else:
                # Otherwise, check token
                token = headers.get("authorization", "")
                if token.startswith("Bearer "):
                    token = token[7:]  # Remove 'Bearer ' prefix
                else:
                    raise AuthenticationError("Missing or invalid Authorization header")
                # Authenticate
                auth_success = self.auth.verify_token(
                    token, client_id=client_id, username=device_id
                )
                if not auth_success:
                    raise AuthenticationError("Invalid token")
