import asyncio
import websockets
from config.logger import setup_logging
from core.connection import ConnectionHandler
from core.utils.util import get_local_ip
from core.utils import asr, vad, llm, tts
from core.utils.performance_monitor import monitor

TAG = __name__

class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self._vad, self._asr, self._llm, self._tts = self._create_processing_instances()
        self._start_perf_monitor()

    def _create_processing_instances(self):
        """创建处理模块实例"""
        return (
            vad.create_instance(
                self.config["selected_module"]["VAD"],
                self.config["VAD"][self.config["selected_module"]["VAD"]]
            ),
            asr.create_instance(
                self.config["selected_module"]["ASR"],
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
            )
        )

    async def start(self):
        server_config = self.config["server"]
        host = server_config["ip"]
        port = server_config["port"]

        self.logger.bind(tag=TAG).info("Server is running at ws://{}:{}", get_local_ip(), port)
        self.logger.bind(tag=TAG).info("=======上面的地址是websocket协议地址，请勿用浏览器访问=======")
        async with websockets.serve(
                self._handle_connection,
                host,
                port
        ):
            await asyncio.Future()

    async def _handle_connection(self, websocket):
        """处理新连接，每次创建独立的ConnectionHandler"""
        handler = ConnectionHandler(self.config, self._vad, self._asr, self._llm, self._tts)
        await handler.handle_connection(websocket)

    def _start_perf_monitor(self):
        async def print_stats():
            while True:
                await asyncio.sleep(30)  # 性能统计时间设置（秒）
                summary = monitor.get_summary()
                print("\n=== 模块性能统计 ===")
                for module, stats in summary.items():
                    print(f"{module}: 平均{stats['avg']:.3f}s | 最大{stats['max']:.3f}s | 最小{stats['min']:.3f}s | 调用次数{stats['total_calls']}")
                print("===================\n")
        
        asyncio.create_task(print_stats())
