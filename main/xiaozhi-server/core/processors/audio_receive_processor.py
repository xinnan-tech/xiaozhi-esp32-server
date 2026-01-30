import time
import json
import asyncio
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.utils.util import audio_to_data
from core.utils.output_counter import check_device_output_limit
from config.logger import setup_logging

logger = setup_logging()


class AudioReceiveProcessor(MessageProcessor):
    """音频接收处理器：完整迁移receiveAudioHandle.py的所有功能"""
    
    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理音频消息"""
        if isinstance(message, bytes):
            await self.handle_audio_message(context, transport, message)
            return True
        return False
    
    async def handle_audio_message(self, context: SessionContext, transport: TransportInterface, audio: bytes):
        """处理音频消息 - 完整迁移自handleAudioMessage"""
        # 获取VAD组件
        vad_component = context.components.get('vad')
        if not vad_component or not hasattr(vad_component, 'vad_instance'):
            logger.warning("VAD组件未初始化")
            return
            
        vad_instance = vad_component.vad_instance
        
        # 当前片段是否有人说话
        have_voice = vad_instance.is_vad(context, audio)
        
        # 如果设备刚刚被唤醒，短暂忽略VAD检测
        if have_voice and context.just_woken_up:
            have_voice = False
            # 设置一个短暂延迟后恢复VAD检测
            context.asr_audio.clear()
            if not hasattr(context, "vad_resume_task") or context.vad_resume_task.done():
                context.vad_resume_task = asyncio.create_task(self._resume_vad_detection(context))
            return
            
        if have_voice:
            if context.is_speaking:
                await self._handle_abort_message(context, transport)
                
        # 设备长时间空闲检测，用于say goodbye
        await self._no_voice_close_connect(context, transport, have_voice)
        
        # 接收音频
        asr_component = context.components.get('asr')
        if asr_component and hasattr(asr_component, 'asr_instance'):
            asr_instance = asr_component.asr_instance
            if hasattr(asr_instance, 'receive_audio'):
                await asr_instance.receive_audio(context, audio, have_voice)
    
    async def _resume_vad_detection(self, context: SessionContext):
        """恢复VAD检测 - 完整迁移自resume_vad_detection"""
        # 等待1秒后恢复VAD检测
        await asyncio.sleep(1)
        context.just_woken_up = False
    
    async def start_to_chat(self, context: SessionContext, transport: TransportInterface, text: str):
        """开始聊天 - 完整迁移自startToChat"""
        # 检查输入是否是JSON格式（包含说话人信息）
        speaker_name = None
        actual_text = text

        try:
            # 尝试解析JSON格式的输入
            if text.strip().startswith('{') and text.strip().endswith('}'):
                data = json.loads(text)
                if 'speaker' in data and 'content' in data:
                    speaker_name = data['speaker']
                    actual_text = data['content']
                    logger.info(f"解析到说话人信息: {speaker_name}")

                    # 直接使用JSON格式的文本，不解析
                    actual_text = text
        except (json.JSONDecodeError, KeyError):
            # 如果解析失败，继续使用原始文本
            pass

        # 保存说话人信息到上下文
        if speaker_name:
            context.current_speaker = speaker_name
        else:
            context.current_speaker = None

        # 检查设备绑定
        if context.need_bind:
            await self._check_bind_device(context, transport)
            return

        # 如果当日的输出字数大于限定的字数
        if context.max_output_size > 0:
            if check_device_output_limit(
                context.headers.get("device-id"), context.max_output_size
            ):
                await self._max_out_size(context, transport)
                return
                
        if context.is_speaking:
            await self._handle_abort_message(context, transport)

        # 首先进行意图分析，使用实际文本内容
        from core.processors.chat_processor import ChatProcessor
        chat_processor = ChatProcessor()
        intent_handled = await chat_processor.handle_user_intent(context, transport, actual_text)

        if intent_handled:
            # 如果意图已被处理，不再进行聊天
            return

        # 意图未被处理，继续常规聊天流程，使用实际文本内容
        await self._send_stt_message(context, transport, actual_text)
        
        # 使用ChatProcessor处理聊天
        from core.processors.chat_processor import ChatProcessor
        chat_processor = ChatProcessor()
        await chat_processor.handle_chat(context, transport, actual_text)

    async def _no_voice_close_connect(self, context: SessionContext, transport: TransportInterface, have_voice: bool):
        """无声音时关闭连接检测 - 完整迁移自no_voice_close_connect"""
        if have_voice:
            context.update_activity()
            return
            
        # 只有在已经初始化过时间戳的情况下才进行超时检查
        if context.last_activity_time_ms > 0.0:
            no_voice_time = time.time() * 1000 - context.last_activity_time_ms
            close_connection_no_voice_time = int(
                context.config.get("close_connection_no_voice_time", 120)
            )
            
            if (
                not context.close_after_chat
                and no_voice_time > 1000 * close_connection_no_voice_time
            ):
                context.close_after_chat = True
                context.abort_requested = False
                
                end_prompt = context.config.get("end_prompt", {})
                if end_prompt and end_prompt.get("enable", True) is False:
                    logger.info("结束对话，无需发送结束提示语")
                    await transport.close()
                    return
                    
                prompt = end_prompt.get("prompt")
                if not prompt:
                    prompt = "请你以```时间过得真快```未来头，用富有感情、依依不舍的话来结束这场对话吧。！"
                await self.start_to_chat(context, transport, prompt)

    async def _max_out_size(self, context: SessionContext, transport: TransportInterface):
        """超出最大输出字数处理 - 完整迁移自max_out_size"""
        # 播放超出最大输出字数的提示
        context.abort_requested = False
        text = "不好意思，我现在有点事情要忙，明天这个时候我们再聊，约好了哦！明天不见不散，拜拜！"
        await self._send_stt_message(context, transport, text)
        
        file_path = "config/assets/max_output_size.wav"
        opus_packets = audio_to_data(file_path)
        
        # 获取TTS组件并添加到队列
        tts_component = context.components.get('tts')
        if tts_component and hasattr(tts_component, 'tts_instance'):
            tts_instance = tts_component.tts_instance
            if hasattr(tts_instance, 'tts_audio_queue'):
                from core.providers.tts.dto.dto import SentenceType
                tts_instance.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
                
        context.close_after_chat = True

    async def _check_bind_device(self, context: SessionContext, transport: TransportInterface):
        """检查设备绑定 - 完整迁移自check_bind_device"""
        bind_code = context.bind_code
        
        if bind_code:
            # 确保bind_code是6位数字
            if len(bind_code) != 6:
                logger.error(f"无效的绑定码格式: {bind_code}")
                text = "绑定码格式错误，请检查配置。"
                await self._send_stt_message(context, transport, text)
                return

            text = f"请登录控制面板，输入{bind_code}，绑定设备。"
            await self._send_stt_message(context, transport, text)

            # 获取TTS组件
            tts_component = context.components.get('tts')
            if not tts_component or not hasattr(tts_component, 'tts_instance'):
                return
                
            tts_instance = tts_component.tts_instance
            if not hasattr(tts_instance, 'tts_audio_queue'):
                return

            # 播放提示音
            from core.providers.tts.dto.dto import SentenceType
            music_path = "config/assets/bind_code.wav"
            opus_packets = audio_to_data(music_path)
            tts_instance.tts_audio_queue.put((SentenceType.FIRST, opus_packets, text))

            # 逐个播放数字
            for i in range(6):  # 确保只播放6位数字
                try:
                    digit = bind_code[i]
                    num_path = f"config/assets/bind_code/{digit}.wav"
                    num_packets = audio_to_data(num_path)
                    tts_instance.tts_audio_queue.put((SentenceType.MIDDLE, num_packets, None))
                except Exception as e:
                    logger.error(f"播放数字音频失败: {e}")
                    continue
            tts_instance.tts_audio_queue.put((SentenceType.LAST, [], None))
        else:
            # 播放未绑定提示
            context.abort_requested = False
            text = f"没有找到该设备的版本信息，请正确配置 OTA地址，然后重新编译固件。"
            await self._send_stt_message(context, transport, text)
            
            # 获取TTS组件
            tts_component = context.components.get('tts')
            if tts_component and hasattr(tts_component, 'tts_instance'):
                tts_instance = tts_component.tts_instance
                if hasattr(tts_instance, 'tts_audio_queue'):
                    from core.providers.tts.dto.dto import SentenceType
                    music_path = "config/assets/bind_not_found.wav"
                    opus_packets = audio_to_data(music_path)
                    tts_instance.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))

    async def _handle_abort_message(self, context: SessionContext, transport: TransportInterface):
        """处理中断消息"""
        logger.info("Audio processor: Abort message received")
        context.abort_requested = True
        
        # 清理队列
        await self._clear_queues(context)
        
        # 打断客户端说话状态
        await transport.send(json.dumps({
            "type": "tts", 
            "state": "stop", 
            "session_id": context.session_id
        }))
        
        # 清理说话状态
        context.is_speaking = False

    async def _clear_queues(self, context: SessionContext):
        """清理所有队列"""
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

    async def _send_stt_message(self, context: SessionContext, transport: TransportInterface, text: str):
        """发送STT消息"""
        await transport.send(json.dumps({
            "type": "stt",
            "text": text,
            "session_id": context.session_id
        }))


