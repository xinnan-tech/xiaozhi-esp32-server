from config.logger import setup_logging
from core.message.sender.message_sender import MessageSender

TAG = __name__
logger = setup_logging()

class WebSocketSender(MessageSender):
    """
    通过一个已存在的 WebSocket 连接发送消息的具体实现。
    """
    def __init__(self, websocket_connection):
        """
        初始化 WebSocketSender。

        Args:
            websocket_connection: 已建立并活跃的 WebSocket 连接实例。
        """
        self.websocket_connection = websocket_connection
        logger.bind(tag=TAG).debug("WebSocketSender: 初始化，使用已存在的 WebSocket 连接")
        if not self.websocket_connection:
            logger.bind(tag=TAG).error("提供的 WebSocket 连接为空或无效。")

    async def send(self, message: str):
        if self.websocket_connection:
            await self.websocket_connection.send(message)
        else:
            logger.bind(tag=TAG).error(f"WebSocket 连接已关闭或无效，无法发送文字消息。")