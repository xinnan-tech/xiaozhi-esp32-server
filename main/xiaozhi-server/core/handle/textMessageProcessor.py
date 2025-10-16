import json

from core.handle.textMessageHandlerRegistry import TextMessageHandlerRegistry

TAG = __name__


class TextMessageProcessor:
    """Message handler main class"""

    def __init__(self, registry: TextMessageHandlerRegistry):
        self.registry = registry

    async def process_message(self, conn, message: str) -> None:
        """The main entry point for processing messages"""
        try:
            # Parsing JSON messages
            msg_json = json.loads(message)

            # Processing JSON messages
            if isinstance(msg_json, dict):
                message_type = msg_json.get("type")

                # Logging
                conn.logger.bind(tag=TAG).info(f"Received {message_type} message: {message}")

                # Get and execute the processor
                handler = self.registry.get_handler(message_type)
                if handler:
                    await handler.handle(conn, msg_json)
                else:
                    conn.logger.bind(tag=TAG).error(f"Received unknown type message: {message}")
            # Processing pure numeric messages
            elif isinstance(msg_json, int):
                conn.logger.bind(tag=TAG).info(f"Received digital message: {message}")
                await conn.websocket.send(message)

        except json.JSONDecodeError:
            # Directly forward non-JSON messages
            conn.logger.bind(tag=TAG).error(f"Parsed error message: {message}")
            await conn.websocket.send(message)