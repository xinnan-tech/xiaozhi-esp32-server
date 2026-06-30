from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType
from core.handle.deviceEventHandle import handle_device_event


class DeviceEventTextMessageHandler(TextMessageHandler):
    """设备事件消息处理器"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.DEVICE_EVENT

    async def handle(self, conn: "ConnectionHandler", msg_json: Dict[str, Any]) -> None:
        await handle_device_event(conn, msg_json)
