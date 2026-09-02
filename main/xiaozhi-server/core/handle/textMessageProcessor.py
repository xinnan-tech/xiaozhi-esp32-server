import json
import asyncio
from core.handle.textMessageHandlerRegistry import TextMessageHandlerRegistry

TAG = __name__

class TextMessageProcessor:
    """Main Message Processor Class"""

    def __init__(self, registry: TextMessageHandlerRegistry):
        self.registry = registry

    async def process_message(self, conn, message: str) -> None:
        """Main entry point for message processing"""
        try:
            # Parse JSON message
            msg_json = json.loads(message)

            # Handle JSON message
            if isinstance(msg_json, dict):
                message_type = msg_json.get("type")

                # SAFE LOGGING: Prevent terminal buffer overflow on large MCP payloads
                if message_type == "mcp":
                    conn.logger.bind(tag=TAG).info(f"Received {message_type} message (Payload hidden for performance)")
                else:
                    conn.logger.bind(tag=TAG).info(f"Received {message_type} message: {message}")

                # TRIGGER: If this is NOT a hello message and MCP is enabled but not ready, 
                # start discovery now so it doesn't block the handshake.
                if message_type != "hello" and conn.features.get("mcp"):
                    if not hasattr(conn, "mcp_client") or conn.mcp_client is None:
                        from core.providers.tools.device_mcp.mcp_handler import (
                            MCPClient, send_mcp_initialize_message, send_mcp_tools_list_request
                        )
                        conn.logger.bind(tag=TAG).info("First user interaction detected. Initializing MCP in background...")
                        conn.mcp_client = MCPClient()
                        asyncio.create_task(send_mcp_initialize_message(conn))
                        asyncio.create_task(send_mcp_tools_list_request(conn))

                # Get and execute the handler
                handler = self.registry.get_handler(message_type)
                if handler:
                    await handler.handle(conn, msg_json)
                else:
                    conn.logger.bind(tag=TAG).error(f"Received unknown message type: {message}")
            
            # Handle numeric messages
            elif isinstance(msg_json, int):
                conn.logger.bind(tag=TAG).info(f"Received numeric message: {message}")
                await conn.websocket.send(message)

        except json.JSONDecodeError:
            # Forward non-JSON messages directly
            conn.logger.bind(tag=TAG).error(f"Failed to parse message: {message}")
            await conn.websocket.send(message)

