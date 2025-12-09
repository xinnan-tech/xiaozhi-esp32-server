from typing import Dict, Any

from core.handle.abortHandle import handleAbortMessage
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType
from config.logger import setup_logging
TAG = __name__
logger = setup_logging()


class AbortTextMessageHandler(TextMessageHandler):
    """Abort消息处理器"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.ABORT

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        conn.logger.bind(tag=TAG).info("Abort message received from client-end in text message format")
        await handleAbortMessage(conn)
