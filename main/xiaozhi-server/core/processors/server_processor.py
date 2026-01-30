import json
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from config.logger import setup_logging

logger = setup_logging()


class ServerProcessor(MessageProcessor):
    """服务器消息处理器：完整迁移serverMessageHandler.py的所有功能"""
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理server类型的消息"""
        if isinstance(message, str):
            try:
                msg_json = json.loads(message)
                if isinstance(msg_json, dict) and msg_json.get("type") == "server":
                    await self.handle_server_message(context, transport, msg_json)
                    return True
            except json.JSONDecodeError:
                pass
        return False
    
    async def handle_server_message(self, context: SessionContext, transport: TransportInterface, msg_json: dict):
        """处理server消息 - 完整迁移自serverMessageHandler.py"""
        # 如果配置是从API读取的，则需要验证secret
        if not context.read_config_from_api:
            return
            
        # 获取post请求的secret
        post_secret = msg_json.get("content", {}).get("secret", "")
        secret = context.config.get("manager-api", {}).get("secret", "")
        
        # 如果secret不匹配，则返回
        if post_secret != secret:
            await self._send_error_response(
                transport, 
                context.session_id,
                "服务器密钥验证失败"
            )
            return
        
        # 处理不同的action
        action = msg_json.get("action")
        
        if action == "update_config":
            await self._handle_update_config(context, transport, msg_json)
        elif action == "restart":
            await self._handle_restart(context, transport, msg_json)
        else:
            await self._send_error_response(
                transport,
                context.session_id,
                f"未知的服务器操作: {action}"
            )
    
    async def _handle_update_config(self, context: SessionContext, transport: TransportInterface, msg_json: dict):
        """处理配置更新 - 完整迁移自update_config逻辑"""
        try:
            # 检查是否有服务器实例
            if not context.server:
                await self._send_error_response(
                    transport,
                    context.session_id,
                    "无法获取服务器实例",
                    {"action": "update_config"}
                )
                return

            # 更新WebSocketServer的配置
            if not await context.server.update_config():
                await self._send_error_response(
                    transport,
                    context.session_id,
                    "更新服务器配置失败",
                    {"action": "update_config"}
                )
                return

            # 发送成功响应
            await self._send_success_response(
                transport,
                context.session_id,
                "配置更新成功",
                {"action": "update_config"}
            )
            
        except Exception as e:
            logger.error(f"更新配置失败: {str(e)}")
            await self._send_error_response(
                transport,
                context.session_id,
                f"更新配置失败: {str(e)}",
                {"action": "update_config"}
            )
    
    async def _handle_restart(self, context: SessionContext, transport: TransportInterface, msg_json: dict):
        """处理服务器重启 - 完整迁移自handle_restart逻辑"""
        try:
            # 这里应该调用context的handle_restart方法
            if hasattr(context, 'handle_restart'):
                await context.handle_restart(msg_json)
            else:
                logger.warning("SessionContext没有handle_restart方法")
                await self._send_error_response(
                    transport,
                    context.session_id,
                    "重启功能暂不可用",
                    {"action": "restart"}
                )
        except Exception as e:
            logger.error(f"处理重启请求失败: {str(e)}")
            await self._send_error_response(
                transport,
                context.session_id,
                f"重启失败: {str(e)}",
                {"action": "restart"}
            )
    
    async def _send_success_response(self, transport: TransportInterface, session_id: str, 
                                   message: str, content: dict = None):
        """发送成功响应"""
        response = {
            "type": "server",
            "status": "success",
            "message": message,
            "session_id": session_id
        }
        if content:
            response["content"] = content
            
        await transport.send(json.dumps(response))
        logger.info(f"服务器操作成功: {message}")
    
    async def _send_error_response(self, transport: TransportInterface, session_id: str,
                                 message: str, content: dict = None):
        """发送错误响应"""
        response = {
            "type": "server",
            "status": "error",
            "message": message,
            "session_id": session_id
        }
        if content:
            response["content"] = content
            
        await transport.send(json.dumps(response))
        logger.error(f"服务器操作失败: {message}")

