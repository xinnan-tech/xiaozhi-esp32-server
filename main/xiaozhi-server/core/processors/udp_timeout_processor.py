import json
from typing import Any

from core.context.session_context import SessionContext
from core.pipeline.message_pipeline import MessageProcessor
from core.transport.transport_interface import TransportInterface
from config.logger import setup_logging

logger = setup_logging()


class UdpTimeoutProcessor(MessageProcessor):
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
        if not isinstance(message, dict) or message.get("type") != "udp_timeout":
            return False
        if not transport.keeps_connection_between_sessions:
            return False

        logger.info(
            "收到udp_timeout: session_id={}", message.get("session_id")
        )
        end_call = getattr(
            getattr(context, "server", None),
            "end_native_mqtt_call",
            None,
        )
        call_ended = False
        if callable(end_call):
            call_ended = await end_call(
                context.device_id,
                "设备UDP接收超时",
                notify_device=True,
                expected_session_id=message.get("session_id"),
            )
        if not call_ended:
            end_conversation = getattr(context, "end_conversation", None)
            if callable(end_conversation):
                await end_conversation(message.get("session_id"))
            await transport.end_session(
                message.get("session_id") or context.session_id
            )
        return True
