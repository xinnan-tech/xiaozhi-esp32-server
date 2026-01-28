from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.auth import AuthMiddleware, AuthenticationError
from config.logger import setup_logging

logger = setup_logging()


class AuthProcessor(MessageProcessor):
    """认证处理器：处理连接认证逻辑"""
    
    def __init__(self):
        self.auth_middleware = None
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理认证相关逻辑"""
        # 如果已经认证，跳过
        if context.is_authenticated:
            return False
        
        # 初始化认证中间件（延迟初始化）
        if self.auth_middleware is None:
            self.auth_middleware = AuthMiddleware(context.config)
        
        # 检查是否为认证消息（通过headers进行认证）
        if context.headers:
            try:
                await self.auth_middleware.authenticate(context.headers)
                context.is_authenticated = True
                logger.info(f"设备认证成功: {context.device_id}")
                return False  # 认证成功，继续处理其他消息
            except AuthenticationError as e:
                logger.error(f"设备认证失败: {e}")
                # 发送认证失败消息
                await transport.send("Authentication failed")
                await transport.close()
                return True  # 认证失败，停止处理
        
        # 如果没有认证信息，要求认证
        await transport.send("Authentication required")
        return True  # 停止后续处理

