import asyncio
import websockets
from config.logger import setup_logging
from core.connection import ConnectionHandler
from config.config_loader import get_config_from_api
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
            False,
            "Memory" in self.config["selected_module"],
            "Intent" in self.config["selected_module"],
        )

        self._vad = modules["vad"] if "vad" in modules else None
        self._asr = modules["asr"] if "asr" in modules else None
        self._llm = modules["llm"] if "llm" in modules else None
        self._intent = modules["intent"] if "intent" in modules else None
        self._memory = modules["memory"] if "memory" in modules else None

        self.active_connections = set()

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("port", 8000))

        async with websockets.serve(
            self._handle_connection, host, port, process_request=self._http_response
        ):
            await asyncio.Future()

    async def _handle_connection(self, websocket):
        """Handle new connection, create independent ConnectionHandler each time"""
        # Pass current server instance when creating ConnectionHandler
        handler = ConnectionHandler(
            self.config,
            self._vad,
            self._asr,
            self._llm,
            self._memory,
            self._intent,
            self,  # Pass server instance
        )

        self.active_connections.add(handler)
        try:
            await handler.handle_connection(websocket)
        finally:
            self.active_connections.discard(handler)

    async def _http_response(self, websocket, request_headers):
        # Check if it's a WebSocket upgrade request
        if request_headers.headers.get("connection", "").lower() == "upgrade":
            # If it's a WebSocket request, return None to allow handshake to continue
            return None
        else:
            # If it's a regular HTTP request, return "server is running"
            return websocket.respond(200, "Server is running\n")

    async def update_config(self) -> bool:
        """Update server configuration and reinitialize components

        Returns:
            bool: Whether update was successful
        """
        try:
            async with self.config_lock:
                # Get configuration again
                new_config = get_config_from_api(self.config)
                if new_config is None:
                    self.logger.bind(tag=TAG).error(
                        "Failed to get new configuration")
                    return False

                self.logger.bind(tag=TAG).info(
                    f"Successfully got new configuration")

                # Check if VAD and ASR types need updating
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)

                self.logger.bind(tag=TAG).info(
                    f"Check if VAD and ASR types need updating: {update_vad} {update_asr}"
                )

                # Update configuration
                self.config = new_config

                # Reinitialize components
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
                if "intent" in modules:
                    self._intent = modules["intent"]
                if "memory" in modules:
                    self._memory = modules["memory"]

                self.logger.bind(tag=TAG).info(
                    f"Configuration update task completed")
                return True

        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Failed to update server configuration: {str(e)}")
            return False
