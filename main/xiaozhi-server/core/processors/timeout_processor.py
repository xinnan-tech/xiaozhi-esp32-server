from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from config.logger import setup_logging

logger = setup_logging()


class TimeoutProcessor(MessageProcessor):
    """超时检查处理器：检查会话是否超时"""

    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """检查会话超时"""
        return await self.handle_timeout(context, transport)

    async def handle_timeout(
        self,
        context: SessionContext,
        transport: TransportInterface,
    ) -> bool:
        """End an expired logical conversation without conflating it with MQTT."""
        if not getattr(context, "conversation_active", False):
            return False

        timeout_seconds = context.config.get("close_connection_no_voice_time", 120)
        if not context.is_timeout(timeout_seconds):
            return False

        try:
            if transport.keeps_connection_between_sessions:
                logger.info(f"会话超时，结束MQTT逻辑会话: {context.session_id}")
                from core.processors.audio_receive_processor import (
                    AudioReceiveProcessor,
                )

                await AudioReceiveProcessor()._no_voice_close_connect(
                    context,
                    transport,
                    have_voice=False,
                )
            else:
                logger.info(f"会话超时，准备关闭连接: {context.session_id}")
                await transport.close()
        except Exception as e:
            logger.error(f"处理超时连接失败: {e}")

        return True
