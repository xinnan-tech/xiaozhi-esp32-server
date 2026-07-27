import json
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from config.logger import setup_logging

logger = setup_logging()


class GoodbyeProcessor(MessageProcessor):
    """Goodbye消息处理器：处理会话结束"""

    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        msg_json = None
        if isinstance(message, str):
            try:
                msg_json = json.loads(message)
            except json.JSONDecodeError:
                msg_json = None
        elif isinstance(message, dict):
            msg_json = message

        if isinstance(msg_json, dict) and msg_json.get("type") == "goodbye":
            logger.info(f"收到goodbye: session_id={msg_json.get('session_id')}")
            # 长连接传输仅结束逻辑会话，短连接传输关闭连接。
            if transport.keeps_connection_between_sessions:
                end_conversation = getattr(context, "end_conversation", None)
                if callable(end_conversation):
                    await end_conversation(msg_json.get("session_id"))
            else:
                await transport.close()
            return True
        return False
