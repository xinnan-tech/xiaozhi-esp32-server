import asyncio
from aiohttp import web
from config.logger import setup_logging
from core.api.ota_handler import OTAHandler
from core.api.vision_handler import VisionHandler
from core.api.memu_handler import MemuHandler

TAG = __name__

# 尝试导入 ChatHistoryHandler（可选）
try:
    from core.api.chat_history_handler import ChatHistoryHandler
    CHAT_HISTORY_AVAILABLE = True
except ImportError as e:
    CHAT_HISTORY_AVAILABLE = False
    print(f"警告: ChatHistoryHandler 不可用 (缺少依赖: {e})，聊天记录API将被禁用")


class SimpleHttpServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()
        self.ota_handler = OTAHandler(config)
        self.vision_handler = VisionHandler(config)
        self.memu_handler = MemuHandler(config)
        
        # 仅在可用时初始化 ChatHistoryHandler
        if CHAT_HISTORY_AVAILABLE:
            try:
                self.chat_history_handler = ChatHistoryHandler(config)
                self.logger.bind(tag=TAG).info("ChatHistoryHandler 初始化成功")
            except Exception as e:
                self.logger.bind(tag=TAG).warning(f"ChatHistoryHandler 初始化失败: {e}")
                self.chat_history_handler = None
        else:
            self.chat_history_handler = None
            self.logger.bind(tag=TAG).info("ChatHistoryHandler 未启用")

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
        read_config_from_api = self.config.get("read_config_from_api", False)
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("http_port", 8003))

        if port:
            app = web.Application()

            if not read_config_from_api:
                # 如果没有开启智控台，只是单模块运行，就需要再添加简单OTA接口，用于下发websocket接口
                app.add_routes(
                    [
                        web.get("/xiaozhi/ota/", self.ota_handler.handle_get),
                        web.post("/xiaozhi/ota/", self.ota_handler.handle_post),
                        web.options("/xiaozhi/ota/", self.ota_handler.handle_post),
                    ]
                )
            # 添加路由
            app.add_routes(
                [
                    web.get("/mcp/vision/explain", self.vision_handler.handle_get),
                    web.post("/mcp/vision/explain", self.vision_handler.handle_post),
                    web.options("/mcp/vision/explain", self.vision_handler.handle_post),
                ]
            )
            
            # 添加 MEMu 记忆管理路由
            app.add_routes(
                [
                    web.post("/api/memu/memories", self.memu_handler.handle_post),
                    web.options("/api/memu/memories", self.memu_handler.handle_options),
                ]
            )
            
            # 添加聊天记录查询路由（仅在可用时）
            if self.chat_history_handler:
                app.add_routes(
                    [
                        web.get("/api/chat-history/session/{session_id}", self.chat_history_handler.handle_get_by_session),
                        web.options("/api/chat-history/session/{session_id}", self.chat_history_handler.handle_options),
                        web.get("/api/chat-history/has-memory/{session_id}", self.chat_history_handler.handle_check_memory),
                        web.options("/api/chat-history/has-memory/{session_id}", self.chat_history_handler.handle_options),
                    ]
                )
                self.logger.bind(tag=TAG).info("聊天记录API路由已启用")
            else:
                self.logger.bind(tag=TAG).info("聊天记录API路由已禁用（ChatHistoryHandler不可用）")

            # 运行服务
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()

            # 保持服务运行
            while True:
                await asyncio.sleep(3600)  # 每隔 1 小时检查一次
