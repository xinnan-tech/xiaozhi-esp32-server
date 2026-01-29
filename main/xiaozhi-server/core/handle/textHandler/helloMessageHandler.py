from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.handle.helloHandle import handleHelloMessage
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType


class HelloTextMessageHandler(TextMessageHandler):
    """Hello消息处理器"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.HELLO

    async def handle(self, conn: "ConnectionHandler", msg_json: Dict[str, Any]) -> None:
        await handleHelloMessage(conn, msg_json)
