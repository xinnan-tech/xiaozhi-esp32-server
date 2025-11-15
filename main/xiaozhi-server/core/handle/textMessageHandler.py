from abc import abstractmethod, ABC
from typing import Dict, Any

from core.handle.textMessageType import TextMessageType

TAG = __name__


class TextMessageHandler(ABC):
    """Message processor abstract base class"""

    @abstractmethod
    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        """Abstract methods for processing messages"""
        pass

    @property
    @abstractmethod
    def message_type(self) -> TextMessageType:
        """Returns the message type processed"""
        pass
