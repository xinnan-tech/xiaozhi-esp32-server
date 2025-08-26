from typing import Dict, Any

from core.handle.messageType import MessageType
from core.handle.textHandler.abortHandle import handleAbortMessage
from core.handle.textHandler.messageHandler import MessageHandler


class AbortMessageHandler(MessageHandler):
    """Abort消息处理器"""

    @property
    def message_type(self) -> MessageType:
        return MessageType.ABORT

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        await handleAbortMessage(conn)
