from typing import Dict, Optional

from core.handle.textHandler.abortMessageHandler import AbortMessageHandler
from core.handle.textHandler.helloMessageHandler import HelloMessageHandler
from core.handle.textHandler.iotMessageHandler import IotMessageHandler
from core.handle.textHandler.listenMessageHandler import ListenMessageHandler
from core.handle.textHandler.mcpMessageHandler import McpMessageHandler
from core.handle.textHandler.messageHandler import MessageHandler
from core.handle.textHandler.serverMessageHandler import ServerMessageHandler

TAG = __name__


class MessageHandlerRegistry:
    """消息处理器注册表"""

    def __init__(self):
        self._handlers: Dict[str, MessageHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """注册默认的消息处理器"""
        handlers = [
            HelloMessageHandler(),
            AbortMessageHandler(),
            ListenMessageHandler(),
            IotMessageHandler(),
            McpMessageHandler(),
            ServerMessageHandler(),
        ]

        for handler in handlers:
            self.register_handler(handler)

    def register_handler(self, handler: MessageHandler) -> None:
        """注册消息处理器"""
        self._handlers[handler.message_type.value] = handler

    def get_handler(self, message_type: str) -> Optional[MessageHandler]:
        """获取消息处理器"""
        return self._handlers.get(message_type)

    def get_supported_types(self) -> list:
        """获取支持的消息类型"""
        return list(self._handlers.keys())
