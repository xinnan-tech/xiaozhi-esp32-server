import asyncio
import json
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.providers.tools.device_mcp import handle_mcp_message
from config.logger import setup_logging

logger = setup_logging()


class McpProcessor(MessageProcessor):
    """MCP消息处理器：完整迁移mcpMessageHandler.py的所有功能"""
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理mcp类型的消息"""
        if isinstance(message, str):
            try:
                msg_json = json.loads(message)
                if isinstance(msg_json, dict) and msg_json.get("type") == "mcp":
                    await self.handle_mcp_message(context, transport, msg_json)
                    return True
            except json.JSONDecodeError:
                pass
        return False
    
    async def handle_mcp_message(self, context: SessionContext, transport: TransportInterface, msg_json: dict):
        """处理MCP消息 - 完整迁移自mcpMessageHandler.py"""
        if "payload" in msg_json:
            # 检查MCP客户端是否存在
            if not context.mcp_client:
                logger.warning("MCP客户端未初始化，无法处理MCP消息")
                await self._send_error_response(transport, context.session_id, "MCP客户端未初始化")
                return
                
            # 创建异步任务处理MCP消息 - 完整迁移原逻辑
            asyncio.create_task(
                self._handle_mcp_payload(context, transport, msg_json["payload"])
            )
        else:
            logger.warning("MCP消息缺少payload字段")
            await self._send_error_response(transport, context.session_id, "MCP消息格式错误：缺少payload")
    
    async def _handle_mcp_payload(self, context: SessionContext, transport: TransportInterface, payload: dict):
        """处理MCP payload - 包装原handle_mcp_message函数"""
        try:
            # 调用原有的handle_mcp_message函数
            # 注意：这里需要传入context而不是conn，因为handle_mcp_message可能需要适配
            await handle_mcp_message(context, context.mcp_client, payload, transport)
            logger.debug("MCP消息处理完成")
            
        except Exception as e:
            logger.error(f"处理MCP消息失败: {e}", exc_info=True)
            await self._send_error_response(
                transport, 
                context.session_id, 
                f"MCP消息处理失败: {str(e)}"
            )
    
    async def _send_error_response(self, transport: TransportInterface, session_id: str, message: str):
        """发送MCP错误响应"""
        response = {
            "type": "mcp",
            "status": "error",
            "message": message,
            "session_id": session_id
        }
        
        try:
            await transport.send(json.dumps(response))
        except Exception as e:
            logger.error(f"发送MCP错误响应失败: {e}")
    
    async def _send_success_response(self, transport: TransportInterface, session_id: str, 
                                   message: str, data: dict = None):
        """发送MCP成功响应"""
        response = {
            "type": "mcp",
            "status": "success", 
            "message": message,
            "session_id": session_id
        }
        if data:
            response["data"] = data
            
        try:
            await transport.send(json.dumps(response))
        except Exception as e:
            logger.error(f"发送MCP成功响应失败: {e}")
