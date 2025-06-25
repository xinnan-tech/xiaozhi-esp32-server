from typing import Dict, Any

from core.message.sender.message_sender import MessageSender
from core.message.sender.websocket_sender import WebSocketSender

class MessageSenderFactory:
    """
    消息发送器的工厂类，根据配置和已存在的连接创建具体的 MessageSender 实例。
    """

    @staticmethod
    def create_sender(config: Dict[str, Any], connection_instance: Any) -> MessageSender:
        """
        根据配置字典和已存在的连接实例创建并返回一个 MessageSender 实例。

        Args:
            config (Dict[str, Any]): 配置字典，至少包含 'message_sender_type' 键，指示使用哪种发送器。
            connection_instance (Any): 已创建并活跃的 WebSocket 连接对象或 MQTT 客户端对象。

        Returns:
            MessageSender: 具体的 MessageSender 实例。

        Raises:
            ValueError: 如果配置中的 'message_sender_type' 不支持或 connection_instance 类型不匹配。
        """
        message_sender_type = config.get("message_sender_type", "websocket")  # 默认使用 websocket 发送器

        if message_sender_type == "websocket":
            return WebSocketSender(connection_instance)
        else:
            raise ValueError(f"不支持的消息发送器类型: {message_sender_type}")