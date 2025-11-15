from core.handle.textMessageHandlerRegistry import TextMessageHandlerRegistry
from core.handle.textMessageProcessor import TextMessageProcessor

TAG = __name__

# Global Processor Registry
message_registry = TextMessageHandlerRegistry()

# Create a global message handler instance
message_processor = TextMessageProcessor(message_registry)

async def handleTextMessage(conn, message):
    """Process text messages"""
    await message_processor.process_message(conn, message)
