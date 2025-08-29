import asyncio
import json
from typing import Dict, Any

from core.handle.messageType import MessageType
from core.handle.textMessageHandler import TextMessageHandler
from core.providers.tools.device_mcp import send_mcp_initialize_message, send_mcp_tools_list_request, MCPClient

TAG = __name__


class HelloTextMessageHandler(TextMessageHandler):
    """Hello消息处理器"""

    @property
    def message_type(self) -> MessageType:
        return MessageType.HELLO

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        audio_params = msg_json.get("audio_params")
        if audio_params:
            audio_format = audio_params.get("format")
            conn.logger.bind(tag=TAG).info(f"客户端音频格式: {audio_format}")
            conn.audio_format = audio_format
            conn.welcome_msg["audio_params"] = audio_params
        features = msg_json.get("features")
        if features:
            conn.logger.bind(tag=TAG).info(f"客户端特性: {features}")
            conn.features = features
            if features.get("mcp"):
                conn.logger.bind(tag=TAG).info("客户端支持MCP")
                conn.mcp_client = MCPClient()
                # 发送初始化
                asyncio.create_task(send_mcp_initialize_message(conn))
                # 发送mcp消息，获取tools列表
                asyncio.create_task(send_mcp_tools_list_request(conn))

        await conn.websocket.send(json.dumps(conn.welcome_msg))
