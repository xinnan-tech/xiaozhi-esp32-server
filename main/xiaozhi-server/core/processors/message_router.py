import json
from typing import Any, List
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.processors.hello_processor import HelloProcessor
from core.processors.listen_processor import ListenProcessor
from core.processors.audio_receive_processor import AudioReceiveProcessor
from core.processors.auth_processor import AuthProcessor
from core.processors.timeout_processor import TimeoutProcessor
from core.processors.server_processor import ServerProcessor
from core.processors.mcp_processor import McpProcessor
from core.processors.iot_processor import IotProcessor
from core.processors.abort_processor import AbortProcessor
from core.processors.text_processor import TextProcessor
from config.logger import setup_logging

logger = setup_logging()


class MessageRouter(MessageProcessor):
    """
    消息路由器：协调所有独立的processor
    按功能职责分离，避免耦合，每个processor专注单一职责
    """
    
    def __init__(self):
        # 初始化所有独立的processor
        self.auth_processor = AuthProcessor()
        self.timeout_processor = TimeoutProcessor()
        self.abort_processor = AbortProcessor()
        self.hello_processor = HelloProcessor()
        self.listen_processor = ListenProcessor()
        self.server_processor = ServerProcessor()
        self.mcp_processor = McpProcessor()
        self.iot_processor = IotProcessor()
        self.audio_receive_processor = AudioReceiveProcessor()
        self.text_processor = TextProcessor()
        
        # 按优先级排序的processor列表
        self.processors: List[MessageProcessor] = [
            self.timeout_processor,    # 首先检查超时
            self.auth_processor,       # 然后检查认证
            self.abort_processor,      # 中断消息
            self.hello_processor,      # hello消息
            self.listen_processor,     # listen消息
            self.server_processor,     # 服务器消息
            self.mcp_processor,        # MCP消息
            self.iot_processor,        # IoT消息
            self.audio_receive_processor,  # 音频消息
            self.text_processor,       # 纯文本消息（放在最后，作为兜底处理）
        ]
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """
        路由消息到合适的processor
        每个processor专注处理自己的消息类型，避免耦合
        """
        # 更新活动时间
        context.update_activity()
        
        # 按优先级顺序尝试每个processor
        for processor in self.processors:
            try:
                if await processor.process(context, transport, message):
                    # 消息已被处理，记录日志并返回
                    logger.debug(f"消息被 {processor.__class__.__name__} 处理")
                    return True
            except Exception as e:
                logger.error(f"{processor.__class__.__name__} 处理消息时出错: {e}", exc_info=True)
                continue
        
        # 如果没有processor处理该消息，记录警告
        if isinstance(message, str):
            try:
                msg_json = json.loads(message)
                msg_type = msg_json.get("type", "unknown") if isinstance(msg_json, dict) else "non-dict"
                logger.warning(f"未处理的消息类型: {msg_type}, 内容: {message[:100]}...")
            except json.JSONDecodeError:
                logger.warning(f"未处理的非JSON消息: {message[:100]}...")
        elif isinstance(message, bytes):
            logger.warning(f"未处理的二进制消息，大小: {len(message)} bytes")
        else:
            logger.warning(f"未处理的消息类型: {type(message)}")
        
        return False
    
    def add_processor(self, processor: MessageProcessor, priority: int = None):
        """
        添加新的processor
        priority: 优先级，数字越小优先级越高，None表示添加到末尾
        """
        if priority is None:
            self.processors.append(processor)
        else:
            self.processors.insert(priority, processor)
        logger.info(f"添加processor: {processor.__class__.__name__}")
    
    def remove_processor(self, processor_class):
        """移除指定类型的processor"""
        self.processors = [p for p in self.processors if not isinstance(p, processor_class)]
        logger.info(f"移除processor: {processor_class.__name__}")
    
    def get_processor(self, processor_class):
        """获取指定类型的processor"""
        for processor in self.processors:
            if isinstance(processor, processor_class):
                return processor
        return None
    
    def list_processors(self) -> List[str]:
        """列出所有processor的名称"""
        return [processor.__class__.__name__ for processor in self.processors]

