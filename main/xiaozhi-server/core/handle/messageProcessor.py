import json

from core.handle.messageHandlerRegistry import MessageHandlerRegistry

TAG = __name__


class MessageProcessor:
    """消息处理器主类"""

    def __init__(self, registry: MessageHandlerRegistry):
        self.registry = registry

    async def process_message(self, conn, message: str) -> None:
        """处理消息的主入口"""
        try:
            # 解析JSON消息
            msg_json = json.loads(message)

            # 处理纯数字消息
            if isinstance(msg_json, int):
                conn.logger.bind(tag=TAG).info(f"收到文本消息：{message}")
                await conn.websocket.send(message)
                return

            message_type = msg_json.get("type")

            # 记录日志
            conn.logger.bind(tag=TAG).info(f"收到{message_type}消息：{message}")

            # 获取并执行处理器
            handler = self.registry.get_handler(message_type)
            if handler:
                await handler.handle(conn, msg_json)
            else:
                conn.logger.bind(tag=TAG).error(f"收到未知类型消息：{message}")

        except json.JSONDecodeError:
            # 非JSON消息直接转发
            conn.logger.bind(tag=TAG).error(f"解析到错误的消息：{message}")
            await conn.websocket.send(message)
