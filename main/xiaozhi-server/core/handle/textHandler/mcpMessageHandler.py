import asyncio
from typing import Dict, Any

from core.handle.messageType import MessageType
from core.handle.textHandler.messageHandler import MessageHandler
from core.providers.tools.device_mcp import handle_mcp_message


class McpMessageHandler(MessageHandler):
    """MCP消息处理器"""

    @property
    def message_type(self) -> MessageType:
        return MessageType.MCP

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        if "payload" in msg_json:
            asyncio.create_task(
                handle_mcp_message(conn, conn.mcp_client, msg_json["payload"])
            )
