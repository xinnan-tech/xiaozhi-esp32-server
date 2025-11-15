import json

from core.handle.textMessageHandlerRegistry import TextMessageHandlerRegistry

TAG = __name__


class TextMessageProcessor:
    """Message processor main class"""

    def __init__(self, registry: TextMessageHandlerRegistry):
        self.registry = registry

    async def process_message(self, conn, message: str) -> None:
        """Main entry point for processing messages"""
        try:
            # Parse json message
            msg_json = json.loads(message)

            # Process json messages
            if isinstance(msg_json, dict):
                message_type = msg_json.get("type")

                # logging
                conn.logger.bind(tag=TAG).info(f"receive{message_type}information:{message}")

                # Get and execute the processor
                handler = self.registry.get_handler(message_type)
                if handler:
                    await handler.handle(conn, msg_json)
                else:
                    conn.logger.bind(tag=TAG).error(f"Unknown type message received:{message}")
            # Handle purely digital messages
            elif isinstance(msg_json, int):
                conn.logger.bind(tag=TAG).info(f"Receive digital message:{message}")
                await conn.websocket.send(message)

        except json.JSONDecodeError:
            # Non-json messages are forwarded directly
            conn.logger.bind(tag=TAG).error(f"Parsed to error message:{message}")
            await conn.websocket.send(message)
