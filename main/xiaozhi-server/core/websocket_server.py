import asyncio
import websockets
from config.logger import setup_logging
from core.connection import ConnectionHandler
from core.utils.util import get_local_ip
from core.utils import asr, vad

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self._vad, self._asr = self._create_processing_instances()
        self.active_connections = set()

    def _create_processing_instances(self):
        """创建处理模块实例"""
        return (
            vad.create_instance(
                self.config["selected_module"]["VAD"],
                self.config["VAD"][self.config["selected_module"]["VAD"]],
            ),
            asr.create_instance(
                (
                    self.config["selected_module"]["ASR"]
                    if not "type"
                    in self.config["ASR"][self.config["selected_module"]["ASR"]]
                    else self.config["ASR"][self.config["selected_module"]["ASR"]][
                        "type"
                    ]
                ),
                self.config["ASR"][self.config["selected_module"]["ASR"]],
                self.config["delete_audio"],
            ),
        )

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
        handler = ConnectionHandler(self.config, self._vad, self._asr)
        self.active_connections.add(handler)
        try:
            await handler.handle_connection(websocket)
        finally:
            self.active_connections.discard(handler)
