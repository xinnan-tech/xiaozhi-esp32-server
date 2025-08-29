from core.handle.textMessageHandlerRegistry import TextMessageHandlerRegistry
from core.handle.textMessageProcessor import TextMessageProcessor

TAG = __name__

# 全局处理器注册表
message_registry = TextMessageHandlerRegistry()

# 创建全局消息处理器实例
message_processor = TextMessageProcessor(message_registry)

async def handleTextMessage(conn, message):
    """处理文本消息"""
    await message_processor.process_message(conn, message)