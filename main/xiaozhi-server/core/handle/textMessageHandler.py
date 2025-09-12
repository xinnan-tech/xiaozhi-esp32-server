from abc import abstractmethod, ABC
from typing import Dict, Any

from core.handle.textMessageType import TextMessageType

TAG = __name__


class TextMessageHandler(ABC):
    """消息处理器抽象基类"""

    @abstractmethod
    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        """处理消息的抽象方法"""
        pass

    @property
    @abstractmethod
    def message_type(self) -> TextMessageType:
        """返回处理的消息类型"""
        pass
