import json
import time
import asyncio
from typing import Any, List
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.providers.tts.dto.dto import SentenceType
from core.utils import textUtils
from config.logger import setup_logging

logger = setup_logging()


class AudioSendProcessor(MessageProcessor):
    """音频发送处理器：完整迁移sendAudioHandle.py的所有功能"""
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """这个处理器不直接处理消息，而是被其他处理器调用"""
        return False
    
    async def send_audio_message(self, context: SessionContext, transport: TransportInterface, 
                                sentence_type: SentenceType, audios: bytes, text: str):
        """发送音频消息 - 完整迁移自sendAudioMessage"""
        tts_component = context.components.get('tts')
        if not tts_component or not hasattr(tts_component, 'tts_instance'):
            return
            
        tts_instance = tts_component.tts_instance
        
        if hasattr(tts_instance, 'tts_audio_first_sentence') and tts_instance.tts_audio_first_sentence:
            logger.info(f"发送第一段语音: {text}")
            tts_instance.tts_audio_first_sentence = False
            await self.send_tts_message(context, transport, "start", None)

        if sentence_type == SentenceType.FIRST:
            await self.send_tts_message(context, transport, "sentence_start", text)

        await self.send_audio(context, transport, audios)
        
        # 发送句子开始消息
        if sentence_type is not SentenceType.MIDDLE:
            logger.info(f"发送音频消息: {sentence_type}, {text}")

        # 发送结束消息（如果是最后一个文本）
        if context.llm_finish_task and sentence_type == SentenceType.LAST:
            await self.send_tts_message(context, transport, "stop", None)
            context.is_speaking = False
            if context.close_after_chat:
                await transport.close()
    
    async def send_audio(self, context: SessionContext, transport: TransportInterface, 
                        audios: bytes, frame_duration: int = 60):
        """发送单个opus包，支持流控 - 完整迁移自sendAudio"""
        if audios is None or len(audios) == 0:
            return

        if isinstance(audios, bytes):
            if context.abort_requested:
                return

            context.update_activity()
            await transport.send(audios)
            await asyncio.sleep(frame_duration / 1000.0)
        elif isinstance(audios, list):
            for audio in audios:
                if context.abort_requested:
                    break
                context.update_activity()
                await transport.send(audio)
                await asyncio.sleep(frame_duration / 1000.0)
    
    async def send_stt_message(self, context: SessionContext, transport: TransportInterface, text: str):
        """发送STT消息 - 完整迁移自send_stt_message"""
        await transport.send(json.dumps({
            "type": "stt",
            "text": text,
            "session_id": context.session_id
        }))
        logger.info(f"发送STT消息: {text}")
    
    async def send_tts_message(self, context: SessionContext, transport: TransportInterface, 
                              state: str, text: str = None):
        """发送TTS消息 - 完整迁移自send_tts_message"""
        message = {
            "type": "tts",
            "state": state,
            "session_id": context.session_id
        }
        if text:
            message["text"] = text
            
        await transport.send(json.dumps(message))
        logger.debug(f"发送TTS消息: state={state}, text={text}")
    
    async def send_music_message(self, context: SessionContext, transport: TransportInterface, 
                                music_path: str, text: str):
        """发送音乐消息 - 完整迁移自send_music_message"""
        from core.utils.util import audio_to_data
        
        try:
            # 获取音频数据
            opus_packets = audio_to_data(music_path)
            if opus_packets:
                # 发送音乐开始消息
                await self.send_tts_message(context, transport, "start", text)
                
                # 发送音频数据
                await self.send_audio(context, transport, opus_packets)
                
                # 发送音乐结束消息
                await self.send_tts_message(context, transport, "stop", None)
                
                logger.info(f"发送音乐: {music_path}")
            else:
                logger.warning(f"无法加载音乐文件: {music_path}")
                
        except Exception as e:
            logger.error(f"发送音乐失败: {e}")
    
    async def send_welcome_audio(self, context: SessionContext, transport: TransportInterface):
        """发送欢迎音频"""
        welcome_audio_path = context.config.get("welcome_audio_path")
        if welcome_audio_path:
            await self.send_music_message(context, transport, welcome_audio_path, "欢迎使用小智助手")
    
    async def send_goodbye_audio(self, context: SessionContext, transport: TransportInterface):
        """发送告别音频"""
        goodbye_audio_path = context.config.get("goodbye_audio_path")
        if goodbye_audio_path:
            await self.send_music_message(context, transport, goodbye_audio_path, "再见，期待下次相遇")

