from core.handle.textMessageHandlerRegistry import TextMessageHandlerRegistry
from core.handle.textMessageProcessor import TextMessageProcessor

TAG = __name__

# Global handler registry
message_registry = TextMessageHandlerRegistry()

# Create global message processor instance
message_processor = TextMessageProcessor(message_registry)

async def handleTextMessage(conn, message):
    """Handle text message"""
    await message_processor.process_message(conn, message)
