import asyncio
from typing import Dict, Any

from core.handle.messageType import MessageType
from core.handle.textHandler.messageHandler import MessageHandler
from core.providers.tools.device_iot import handleIotDescriptors, handleIotStatus


class IotMessageHandler(MessageHandler):
    """IoT消息处理器"""

    @property
    def message_type(self) -> MessageType:
        return MessageType.IOT

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        if "descriptors" in msg_json:
            asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
        if "states" in msg_json:
            asyncio.create_task(handleIotStatus(conn, msg_json["states"]))
