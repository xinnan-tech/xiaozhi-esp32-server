import time
import json
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.utils.util import remove_punctuation_and_length
from config.logger import setup_logging

logger = setup_logging()


class ListenProcessor(MessageProcessor):
    """Listen消息处理器：完整迁移listenMessageHandler.py的所有功能"""
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理listen类型的消息"""
        if isinstance(message, str):
            try:
                msg_json = json.loads(message)
                if isinstance(msg_json, dict) and msg_json.get("type") == "listen":
                    await self.handle_listen_message(context, transport, msg_json)
                    return True
            except json.JSONDecodeError:
                pass
        return False
    
    async def handle_listen_message(self, context: SessionContext, transport: TransportInterface, msg_json: dict):
        """处理listen消息 - 完整迁移自listenMessageHandler.py"""
        # 设置拾音模式
        if "mode" in msg_json:
            context.listen_mode = msg_json["mode"]
            logger.debug(f"客户端拾音模式：{context.listen_mode}")
        
        # 处理不同的状态
        state = msg_json.get("state")
        
        if state == "start":
            # 开始监听语音
            context.client_have_voice = True
            context.client_voice_stop = False
            logger.debug("开始语音监听")
            
        elif state == "stop":
            # 停止监听语音
            context.client_have_voice = True
            context.client_voice_stop = True
            # 如果有音频数据，处理最后的音频
            if len(context.asr_audio) > 0:
                await self._handle_audio_message(context, transport, b"")
            logger.debug("停止语音监听")
            
        elif state == "detect":
            # 检测到文本输入
            context.client_have_voice = False
            context.asr_audio.clear()
            
            if "text" in msg_json:
                context.update_activity()
                original_text = msg_json["text"]  # 保留原始文本
                filtered_len, filtered_text = remove_punctuation_and_length(original_text)

                # 识别是否是唤醒词
                is_wakeup_words = filtered_text in context.config.get("wakeup_words", [])
                # 是否开启唤醒词回复
                enable_greeting = context.config.get("enable_greeting", True)

                if is_wakeup_words and not enable_greeting:
                    # 如果是唤醒词，且关闭了唤醒词回复，就不用回答
                    await self._send_stt_message(context, transport, original_text)
                    await self._send_tts_message(context, transport, "stop", None)
                    context.is_speaking = False
                    
                elif is_wakeup_words:
                    # 处理唤醒词
                    context.just_woken_up = True
                    # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                    await self._enqueue_asr_report(context, "嘿，你好呀", [])
                    await self._start_to_chat(context, transport, "嘿，你好呀")
                    
                else:
                    # 处理普通文本
                    # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                    await self._enqueue_asr_report(context, original_text, [])
                    # 否则需要LLM对文字内容进行答复
                    await self._start_to_chat(context, transport, original_text)
    
    async def _handle_audio_message(self, context: SessionContext, transport: TransportInterface, audio: bytes):
        """处理音频消息 - 调用AudioReceiveProcessor"""
        # 这里应该调用AudioReceiveProcessor来处理音频
        from core.processors.audio_receive_processor import AudioReceiveProcessor
        audio_processor = AudioReceiveProcessor()
        await audio_processor.handle_audio_message(context, transport, audio)
    
    async def _send_stt_message(self, context: SessionContext, transport: TransportInterface, text: str):
        """发送STT消息"""
        await transport.send(json.dumps({
            "type": "stt",
            "text": text,
            "session_id": context.session_id
        }))
        logger.info(f"发送STT消息: {text}")
    
    async def _send_tts_message(self, context: SessionContext, transport: TransportInterface, state: str, text: str = None):
        """发送TTS消息"""
        message = {
            "type": "tts",
            "state": state,
            "session_id": context.session_id
        }
        if text:
            message["text"] = text
            
        await transport.send(json.dumps(message))
        logger.debug(f"发送TTS消息: state={state}, text={text}")
    
    async def _enqueue_asr_report(self, context: SessionContext, text: str, audio_data: list):
        """ASR上报队列"""
        if context.report_asr_enable:
            from core.processors.report_processor import ReportProcessor
            report_processor = ReportProcessor()
            report_processor.enqueue_asr_report(context, text, audio_data)
    
    async def _start_to_chat(self, context: SessionContext, transport: TransportInterface, text: str):
        """开始聊天 - 调用ChatProcessor"""
        from core.processors.chat_processor import ChatProcessor
        chat_processor = ChatProcessor()
        await chat_processor.handle_chat(context, transport, text)

