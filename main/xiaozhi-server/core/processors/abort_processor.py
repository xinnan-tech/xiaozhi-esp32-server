import json
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from config.logger import setup_logging

logger = setup_logging()


class AbortProcessor(MessageProcessor):
    """中断消息处理器：完整迁移abortMessageHandler.py和abortHandle.py的所有功能"""
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理abort类型的消息"""
        if isinstance(message, str):
            try:
                msg_json = json.loads(message)
                if isinstance(msg_json, dict) and msg_json.get("type") == "abort":
                    await self.handle_abort_message(context, transport, msg_json)
                    return True
            except json.JSONDecodeError:
                pass
        return False
    
    async def handle_abort_message(self, context: SessionContext, transport: TransportInterface, msg_json: dict):
        """处理中断消息 - 完整迁移自abortHandle.py的handleAbortMessage"""
        logger.info("Abort message received")
        
        # 设置成打断状态，会自动打断llm、tts任务 - 完整迁移原逻辑
        context.abort_requested = True
        
        # 清理队列 - 完整迁移原逻辑
        await self._clear_queues(context)
        
        # 打断客户端说话状态 - 完整迁移原逻辑
        await transport.send(json.dumps({
            "type": "tts", 
            "state": "stop", 
            "session_id": context.session_id
        }))
        
        # 清理说话状态 - 完整迁移原逻辑
        self._clear_speak_status(context)
        
        logger.info("Abort message received-end")
    
    async def _clear_queues(self, context: SessionContext):
        """清理所有队列 - 完整迁移原clear_queues逻辑"""
        try:
            # 清理TTS音频队列
            tts_component = context.components.get('tts')
            if tts_component and hasattr(tts_component, 'tts_instance'):
                tts_instance = tts_component.tts_instance
                if hasattr(tts_instance, 'tts_audio_queue'):
                    try:
                        while not tts_instance.tts_audio_queue.empty():
                            tts_instance.tts_audio_queue.get_nowait()
                    except:
                        pass
            
            # 清理ASR音频队列
            context.clear_audio_buffer()
            
            # 清理其他可能的队列
            if hasattr(context, 'clear_queues'):
                context.clear_queues()
                
        except Exception as e:
            logger.error(f"清理队列时出错: {e}")
    
    def _clear_speak_status(self, context: SessionContext):
        """清理说话状态 - 完整迁移原clearSpeakStatus逻辑"""
        try:
            # 清理说话状态
            context.is_speaking = False
            
            # 如果有其他说话状态相关的属性，也一并清理
            if hasattr(context, 'clearSpeakStatus'):
                context.clearSpeakStatus()
            
            # 重置相关状态
            context.client_have_voice = False
            context.client_voice_stop = True
            
        except Exception as e:
            logger.error(f"清理说话状态时出错: {e}")
    
    async def _send_abort_confirmation(self, transport: TransportInterface, session_id: str):
        """发送中断确认响应（可选）"""
        response = {
            "type": "abort",
            "status": "success",
            "message": "中断操作已完成",
            "session_id": session_id
        }
        
        try:
            await transport.send(json.dumps(response))
        except Exception as e:
            logger.error(f"发送中断确认响应失败: {e}")

