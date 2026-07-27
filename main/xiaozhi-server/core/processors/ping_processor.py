import json
import time
from typing import Any

from core.context.session_context import SessionContext
from core.pipeline.message_pipeline import MessageProcessor
from core.transport.transport_interface import TransportInterface
from config.logger import setup_logging

logger = setup_logging()


class PingProcessor(MessageProcessor):
    """Handle the optional legacy JSON ping/pong control contract."""

    async def process(
        self,
        context: SessionContext,
        transport: TransportInterface,
        message: Any,
    ) -> bool:
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except json.JSONDecodeError:
                return False
        if not isinstance(message, dict) or message.get("type") != "ping":
            return False

        if not context.config.get("enable_websocket_ping", False):
            logger.debug("WebSocket心跳功能未启用，忽略PING消息")
            return True

        await transport.send_json(
            {
                "type": "pong",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            }
        )
        return True
