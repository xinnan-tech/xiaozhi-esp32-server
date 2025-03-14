import asyncio
import websockets
from config.logger import setup_logging
from core.connection import ConnectionHandler
from core.handle.musicHandler import MusicHandler
from core.utils.util import get_local_ip
from core.utils import asr, vad, llm, tts, memory

# 获取当前模块的名称作为日志标签
TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        """
        初始化WebSocket服务器。

        :param config: 包含服务器配置和模块选择的字典。
        """
        self.config = config
        self.logger = setup_logging()  # 初始化日志记录器
        # 创建处理模块的实例
        self._vad, self._asr, self._llm, self._tts, self._music, self._memory = self._create_processing_instances()
        self.active_connections = set()  # 用于记录当前活动的连接

    def _create_processing_instances(self):
        """
        根据配置创建各个处理模块的实例。

        :return: 返回一个包含各个模块实例的元组。
        """
        # 获取配置中选择的Memory模块名称，默认为'mem0ai'
        memory_cls_name = self.config["selected_module"].get("Memory", "mem0ai")
        # 检查配置中是否存在Memory模块的配置
        has_memory_cfg = self.config.get("Memory") and memory_cls_name in self.config["Memory"]
        # 获取Memory模块的配置，如果不存在则使用空字典
        memory_cfg = self.config["Memory"][memory_cls_name] if has_memory_cfg else {}

        # 创建各个处理模块的实例
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
            MusicHandler(self.config),  # 创建音乐处理模块的实例
            memory.create_instance(memory_cls_name, memory_cfg),  # 创建记忆模块的实例
        )

    async def start(self):
        """
        启动WebSocket服务器。
        """
        server_config = self.config["server"]
        host = server_config["ip"]  # 获取服务器IP地址
        port = server_config["port"]  # 获取服务器端口号

        # 记录服务器启动信息
        self.logger.bind(tag=TAG).info("Server is running at ws://{}:{}", get_local_ip(), port)
        self.logger.bind(tag=TAG).info("=======上面的地址是websocket协议地址，请勿用浏览器访问=======")

        # 启动WebSocket服务器
        async with websockets.serve(
                self._handle_connection,
                host,
                port
        ):
            await asyncio.Future()  # 保持服务器运行

    async def _handle_connection(self, websocket):
        """
        处理新的WebSocket连接。

        :param websocket: 新的WebSocket连接对象。
        """
        # 创建ConnectionHandler实例，传入当前server实例和各个处理模块
        handler = ConnectionHandler(self.config, self._vad, self._asr, self._llm, self._tts, self._music, self._memory)
        self.active_connections.add(handler)  # 将新连接添加到活动连接集合中
        try:
            await handler.handle_connection(websocket)  # 处理连接
        finally:
            self.active_connections.discard(handler)  # 连接结束后从活动连接集合中移除