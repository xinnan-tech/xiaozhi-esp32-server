import asyncio
import websockets
import ssl
import os
from config.logger import setup_logging
from core.connection import ConnectionHandler
from core.handle.musicHandler import MusicHandler
from core.utils.util import get_local_ip
from core.utils import asr, vad, llm, tts, memory

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self._vad, self._asr, self._llm, self._tts, self._music, self._memory = self._create_processing_instances()
        self.active_connections = set()  # 添加全局连接记录

    def _create_processing_instances(self):
        memory_cls_name = self.config["selected_module"].get("Memory", "mem0ai") # 默认使用mem0ai
        has_memory_cfg = self.config.get("Memory") and memory_cls_name in self.config["Memory"]
        memory_cfg = self.config["Memory"][memory_cls_name] if has_memory_cfg else {}

        """创建处理模块实例"""
        return (
            vad.create_instance(
                self.config["selected_module"]["VAD"],
                self.config["VAD"][self.config["selected_module"]["VAD"]]
            ),
            asr.create_instance(
                self.config["selected_module"]["ASR"]
                if not 'type' in self.config["ASR"][self.config["selected_module"]["ASR"]]
                else
                self.config["ASR"][self.config["selected_module"]["ASR"]]["type"],
                self.config["ASR"][self.config["selected_module"]["ASR"]],
                self.config["delete_audio"]
            ),
            llm.create_instance(
                self.config["selected_module"]["LLM"]
                if not 'type' in self.config["LLM"][self.config["selected_module"]["LLM"]]
                else
                self.config["LLM"][self.config["selected_module"]["LLM"]]['type'],
                self.config["LLM"][self.config["selected_module"]["LLM"]],
            ),
            tts.create_instance(
                self.config["selected_module"]["TTS"]
                if not 'type' in self.config["TTS"][self.config["selected_module"]["TTS"]]
                else
                self.config["TTS"][self.config["selected_module"]["TTS"]]["type"],
                self.config["TTS"][self.config["selected_module"]["TTS"]],
                self.config["delete_audio"]
            ),
            MusicHandler(self.config),
            memory.create_instance(memory_cls_name, memory_cfg),
        )

    async def start(self):
        server_config = self.config["server"]
        host = server_config["ip"]
        port = server_config["port"]
        
        # 创建 SSL 上下文
        ssl_context = None
        if server_config.get("use_ssl", True):  # 默认启用 SSL
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            cert_path = os.path.join("data", "server.crt")
            key_path = os.path.join("data", "server.key")
            ssl_context.load_cert_chain(cert_path, key_path)

        protocol = "wss" if ssl_context else "ws"
        self.logger.bind(tag=TAG).info("Server is running at {}://{}:{}", protocol, get_local_ip(), port)
        self.logger.bind(tag=TAG).info("=======上面的地址是websocket协议地址，请勿用浏览器访问=======")
        
        async with websockets.serve(
                self._handle_connection,
                host,
                port,
                ssl=ssl_context
        ):
            await asyncio.Future()

    async def _handle_connection(self, websocket):
        """处理新连接，每次创建独立的ConnectionHandler"""
        # 创建ConnectionHandler时传入当前server实例
        handler = ConnectionHandler(self.config, self._vad, self._asr, self._llm, self._tts, self._music, self._memory)
        self.active_connections.add(handler)
        try:
            await handler.handle_connection(websocket)
        finally:
            self.active_connections.discard(handler)
