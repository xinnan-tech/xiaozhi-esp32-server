from typing import Dict, Any

from core.handle.abortHandle import handleAbortMessage
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType


class AbortTextMessageHandler(TextMessageHandler):
    """Abort消息处理器"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.ABORT

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        await handleAbortMessage(conn)
