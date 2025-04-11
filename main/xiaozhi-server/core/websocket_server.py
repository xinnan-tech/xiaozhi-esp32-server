import asyncio
import websockets
from config.logger import setup_logging
from core.connection import ConnectionHandler
from core.utils.util import get_local_ip, initialize_modules

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        modules = initialize_modules(self.config)
        self._vad = modules["vad"]
        self._asr = modules["asr"]
        self._tts = modules["tts"]
        self._llm = modules["llm"]
        self._intent = modules["intent"]
        self._memory = modules["memory"]
        self.active_connections = set()

    async def start(self):
        server_config = self.config["server"]
        host = server_config["ip"]
        port = server_config["port"]

        self.logger.bind(tag=TAG).info(
            "Server is running at ws://{}:{}/xiaozhi/v1/", get_local_ip(), port
        )
        self.logger.bind(tag=TAG).info(
            "=======上面的地址是websocket协议地址，请勿用浏览器访问======="
        )
        self.logger.bind(tag=TAG).info(
            "如想测试websocket请用谷歌浏览器打开test目录下的test_page.html"
        )
        self.logger.bind(tag=TAG).info(
            "=============================================================\n"
        )
        async with websockets.serve(self._handle_connection, host, port):
            await asyncio.Future()

    async def _handle_connection(self, websocket):
        """处理新连接，每次创建独立的ConnectionHandler"""
        # 创建ConnectionHandler时传入当前server实例
        handler = ConnectionHandler(
            self.config,
            self._vad,
            self._asr,
            self._llm,
            self._tts,
            self._memory,
            self._intent,
        )
        self.active_connections.add(handler)
        try:
            await handler.handle_connection(websocket)
        finally:
            self.active_connections.discard(handler)
