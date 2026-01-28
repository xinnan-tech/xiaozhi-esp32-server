import json
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
        # 更新活动时间（在其他处理器中已更新，这里只检查）
        
        # 获取超时配置
        timeout_seconds = context.config.get("close_connection_no_voice_time", 120)
        
        # 检查是否超时
        if context.is_timeout(timeout_seconds):
            logger.info(f"会话超时，准备关闭连接: {context.session_id}")
            
            # 发送超时通知
            timeout_msg = {
                "type": "timeout",
                "message": "连接超时，即将关闭",
                "session_id": context.session_id
            }
            
            try:
                await transport.send(json.dumps(timeout_msg))
                await transport.close()
            except Exception as e:
                logger.error(f"发送超时消息失败: {e}")
            
            return True  # 消息已处理，停止后续处理
        
        return False  # 未超时，继续处理

