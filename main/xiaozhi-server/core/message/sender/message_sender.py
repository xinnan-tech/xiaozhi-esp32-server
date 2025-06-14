from abc import ABC, abstractmethod

class MessageSender(ABC):
    """
    消息发送的抽象基类。
    定义了所有消息发送器都应该实现的发送接口。
    """

    @abstractmethod
    def send(self, message: any):
        """
        抽象方法：发送消息。

        Args:
            message (any): 要发送的内容。
        """
        pass