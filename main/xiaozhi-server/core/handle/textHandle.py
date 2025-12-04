from core.handle.textMessageHandlerRegistry import TextMessageHandlerRegistry
from core.handle.textMessageProcessor import TextMessageProcessor
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# 全局处理器注册表
message_registry = TextMessageHandlerRegistry()

# 创建全局消息处理器实例
message_processor = TextMessageProcessor(message_registry)

async def handleTextMessage(conn, message):
    """处理文本消息"""
    logger.bind(tag=TAG).info(f"收到文本消息: {message}")
    await message_processor.process_message(conn, message)
