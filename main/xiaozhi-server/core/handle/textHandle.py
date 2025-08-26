from core.handle.messageHandlerRegistry import MessageHandlerRegistry
from core.handle.messageProcessor import MessageProcessor

TAG = __name__

# 全局处理器注册表
message_registry = MessageHandlerRegistry()

# 创建全局消息处理器实例
message_processor = MessageProcessor(message_registry)

async def handleTextMessage(conn, message):
    """处理文本消息"""
    await message_processor.process_message(conn, message)