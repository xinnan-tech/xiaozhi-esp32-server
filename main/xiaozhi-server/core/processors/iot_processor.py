import asyncio
import json
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.providers.tools.device_iot import handleIotStatus, handleIotDescriptors
from config.logger import setup_logging

logger = setup_logging()


class IotProcessor(MessageProcessor):
    """IoT消息处理器：完整迁移iotMessageHandler.py的所有功能"""
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理iot类型的消息"""
        if isinstance(message, str):
            try:
                msg_json = json.loads(message)
                if isinstance(msg_json, dict) and msg_json.get("type") == "iot":
                    await self.handle_iot_message(context, transport, msg_json)
                    return True
            except json.JSONDecodeError:
                pass
        return False
    
    async def handle_iot_message(self, context: SessionContext, transport: TransportInterface, msg_json: dict):
        """处理IoT消息 - 完整迁移自iotMessageHandler.py"""
        tasks = []
        
        # 处理设备描述符 - 完整迁移原逻辑
        if "descriptors" in msg_json:
            logger.debug("处理IoT设备描述符")
            task = asyncio.create_task(
                self._handle_iot_descriptors(context, transport, msg_json["descriptors"])
            )
            tasks.append(task)
        
        # 处理设备状态 - 完整迁移原逻辑
        if "states" in msg_json:
            logger.debug("处理IoT设备状态")
            task = asyncio.create_task(
                self._handle_iot_status(context, transport, msg_json["states"])
            )
            tasks.append(task)
        
        # 如果没有有效的IoT数据
        if not tasks:
            logger.warning("IoT消息缺少descriptors或states字段")
            await self._send_error_response(
                transport, 
                context.session_id, 
                "IoT消息格式错误：缺少descriptors或states字段"
            )
            return
        
        # 等待所有任务完成（可选，根据原逻辑决定）
        # await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _handle_iot_descriptors(self, context: SessionContext, transport: TransportInterface, descriptors: Any):
        """处理IoT设备描述符 - 包装原handleIotDescriptors函数"""
        try:
            # 调用原有的handleIotDescriptors函数
            # 注意：这里需要传入context而不是conn，因为handleIotDescriptors可能需要适配
            await handleIotDescriptors(context, descriptors)
            logger.debug("IoT设备描述符处理完成")
            
        except Exception as e:
            logger.error(f"处理IoT设备描述符失败: {e}", exc_info=True)
            await self._send_error_response(
                transport, 
                context.session_id, 
                f"IoT设备描述符处理失败: {str(e)}"
            )
    
    async def _handle_iot_status(self, context: SessionContext, transport: TransportInterface, states: Any):
        """处理IoT设备状态 - 包装原handleIotStatus函数"""
        try:
            # 调用原有的handleIotStatus函数
            # 注意：这里需要传入context而不是conn，因为handleIotStatus可能需要适配
            await handleIotStatus(context, states)
            logger.debug("IoT设备状态处理完成")
            
        except Exception as e:
            logger.error(f"处理IoT设备状态失败: {e}", exc_info=True)
            await self._send_error_response(
                transport, 
                context.session_id, 
                f"IoT设备状态处理失败: {str(e)}"
            )
    
    async def _send_error_response(self, transport: TransportInterface, session_id: str, message: str):
        """发送IoT错误响应"""
        response = {
            "type": "iot",
            "status": "error",
            "message": message,
            "session_id": session_id
        }
        
        try:
            await transport.send(json.dumps(response))
        except Exception as e:
            logger.error(f"发送IoT错误响应失败: {e}")
    
    async def _send_success_response(self, transport: TransportInterface, session_id: str, 
                                   message: str, data: dict = None):
        """发送IoT成功响应"""
        response = {
            "type": "iot",
            "status": "success",
            "message": message,
            "session_id": session_id
        }
        if data:
            response["data"] = data
            
        try:
            await transport.send(json.dumps(response))
        except Exception as e:
            logger.error(f"发送IoT成功响应失败: {e}")

