from typing import Dict, Any

from core.handle.helloHandle import handleHelloMessage
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType


class HelloTextMessageHandler(TextMessageHandler):
    """Hello消息处理器"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.HELLO

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        await handleHelloMessage(conn, msg_json)