import asyncio
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType
from core.providers.tools.device_iot import handleIotStatus, handleIotDescriptors


class IotTextMessageHandler(TextMessageHandler):
    """IOT消息处理器"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.IOT

    async def handle(self, conn: "ConnectionHandler", msg_json: Dict[str, Any]) -> None:
        if "descriptors" in msg_json:
            asyncio.create_task(handleIotDescriptors(conn, msg_json["descriptors"]))
        if "states" in msg_json:
            asyncio.create_task(handleIotStatus(conn, msg_json["states"]))