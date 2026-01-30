import json
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from config.logger import setup_logging

logger = setup_logging()


class TextProcessor(MessageProcessor):
    """
    纯文本消息处理器：处理非JSON格式的文本消息
    这是新架构中缺失的重要组件，用于处理直接发送的文本聊天内容
    """
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理纯文本消息"""
        if isinstance(message, str):
            try:
                # 尝试解析为JSON，如果成功则不是纯文本消息
                json.loads(message)
                return False  # JSON消息由其他processor处理
            except json.JSONDecodeError:
                # 确实是纯文本消息，进行聊天处理
                await self.handle_text_message(context, transport, message)
                return True
        return False
    
    async def handle_text_message(self, context: SessionContext, transport: TransportInterface, text: str):
        """处理纯文本消息 - 直接调用ChatProcessor进行聊天"""
        try:
            # 记录收到纯文本消息
            logger.info(f"收到纯文本消息: {text[:100]}...")
            
            # 使用ChatProcessor处理聊天
            from core.processors.chat_processor import ChatProcessor
            chat_processor = ChatProcessor()
            await chat_processor.handle_chat(context, transport, text)
            
        except Exception as e:
            logger.error(f"处理纯文本消息失败: {e}")
            # 发送错误响应
            await self._send_error_response(transport, "文本处理失败，请重试")
    
    async def _send_error_response(self, transport: TransportInterface, error_message: str):
        """发送错误响应"""
        try:
            await transport.send(json.dumps({
                "type": "error",
                "message": error_message
            }))
        except Exception as e:
            logger.error(f"发送错误响应失败: {e}")

