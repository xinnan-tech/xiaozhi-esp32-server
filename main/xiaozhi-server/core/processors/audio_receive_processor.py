import time
import json
import asyncio
import uuid
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.components.component_manager import ComponentType
from core.services.audio_ingress_service import AudioIngressService
from core.utils.util import audio_to_data
from core.utils.output_counter import check_device_output_limit
from config.logger import setup_logging

logger = setup_logging()


def arm_wake_audio_suppression(context: SessionContext) -> None:
    """Ignore reordered wake-word audio for a bounded interval."""
    context.just_woken_up = True
    previous = getattr(context, "wake_audio_suppression_task", None)
    if previous and not previous.done():
        previous.cancel()

    delay_ms = max(
        0,
        int(context.config.get("wake_audio_suppression_ms", 2000)),
    )
    if delay_ms == 0:
        context.just_woken_up = False
        context.wake_audio_suppression_task = None
        return

    session_id = context.session_id
    context.wake_audio_suppression_task = context.create_background_task(
        _release_wake_audio_suppression(
            context,
            session_id,
            delay_ms / 1000,
        ),
        conversation_scoped=True,
    )


async def _release_wake_audio_suppression(
    context: SessionContext,
    session_id: str,
    delay_seconds: float,
) -> None:
    current_task = asyncio.current_task()
    try:
        await asyncio.sleep(delay_seconds)
        if context.session_id == session_id:
            context.just_woken_up = False
    finally:
        if getattr(context, "wake_audio_suppression_task", None) is current_task:
            context.wake_audio_suppression_task = None


class AudioReceiveProcessor(MessageProcessor):
    """音频接收处理器：完整迁移receiveAudioHandle.py的所有功能"""

    def __init__(self, audio_ingress_service=None):
        self.audio_ingress_service = audio_ingress_service or AudioIngressService()

    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理音频消息"""
        if isinstance(message, bytes):
            await self.handle_audio_message(context, transport, message, 0)
            return True
        if isinstance(message, dict) and message.get("type") == "audio":
            audio_data = message.get("data")
            if isinstance(audio_data, (bytes, bytearray)):
                await self.handle_audio_message(
                    context,
                    transport,
                    bytes(audio_data),
                    int(message.get("timestamp", 0) or 0),
                )
                return True
            return True
        return False

    async def handle_audio_message(
        self,
        context: SessionContext,
        transport: TransportInterface,
        audio: bytes,
        timestamp: int = 0,
    ):
        """处理音频消息 - 完整迁移自handleAudioMessage"""
        if (
            getattr(transport, "requires_audio_tail_grace", False)
            and not getattr(context, "accepting_input_audio", False)
        ):
            return

        pcm_frame = self.audio_ingress_service.process(context, audio, timestamp)
        if not pcm_frame:
            return

        # Do not feed encoded wake-word history into stateful VAD. Native MQTT
        # gates the usual pre-start history above; this bounded suppression only
        # covers frames that crossed the independent control/audio channels.
        if context.just_woken_up:
            if not getattr(context, "wake_audio_suppression_task", None):
                arm_wake_audio_suppression(context)
            context.asr_audio.clear()
            context.reset_vad_states()
            return

        # 获取VAD组件
        vad_component = await self._get_component(context, ComponentType.VAD)
        if not vad_component or not hasattr(vad_component, 'vad_instance'):
            now = time.time()
            last_log = getattr(context, "_vad_missing_last_log", 0.0)
            if now - last_log > 10:
                logger.warning("VAD组件未初始化")
                context._vad_missing_last_log = now
            return

        vad_instance = vad_component.vad_instance

        # 当前片段是否有人说话
        have_voice = vad_instance.is_vad(context, pcm_frame)

        if have_voice:
            if (
                getattr(context, "client_aec", False)
                and context.is_speaking
                and context.listen_mode != "manual"
            ):
                await self._handle_abort_message(context, transport)

        # 设备长时间空闲检测，用于say goodbye
        await self._no_voice_close_connect(context, transport, have_voice)

        # 接收音频
        asr_component = await self._get_component(context, ComponentType.ASR)
        asr_instance = asr_component.asr_instance if asr_component and hasattr(asr_component, 'asr_instance') else None

        # 自动模式兜底：没有收到 listen stop 时，基于VAD触发一次停止
        if (
            not have_voice
            and context.client_have_voice
            and not context.client_voice_stop
            and not getattr(context, "listen_stop_pending", False)
            and context.listen_mode != "manual"
            and asr_instance is not None
        ):
            context.client_voice_stop = True
            try:
                from core.providers.asr.dto.dto import InterfaceType
                if hasattr(asr_instance, "interface_type") and asr_instance.interface_type == InterfaceType.STREAM:
                    if hasattr(asr_instance, "_send_stop_request"):
                        context.create_background_task(
                            asr_instance._send_stop_request(),
                            turn_scoped=True,
                        )
                else:
                    if len(context.asr_audio) > 0:
                        asr_audio_task = context.asr_audio.copy()
                        context.asr_audio.clear()
                        context.reset_vad_states()
                        await asr_instance.handle_voice_stop(context, asr_audio_task)
            except Exception as e:
                logger.error(f"自动VAD停止处理失败: {e}")

        if asr_instance and hasattr(asr_instance, 'receive_audio'):
            await asr_instance.receive_audio(context, pcm_frame, have_voice)

    async def start_to_chat(
        self,
        context: SessionContext,
        transport: TransportInterface,
        text: str,
        *,
        preserve_close_after_chat: bool = False,
    ):
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
                    actual_content = data['content']
                    logger.info(f"解析到说话人信息: {speaker_name}")

                    if speaker_name not in context.introduced_speakers:
                        context.introduced_speakers.add(speaker_name)
                        actual_text = text
                    else:
                        actual_text = actual_content
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
            await self.prompt_bind_device(context, transport)
            return

        # 如果当日的输出字数大于限定的字数
        if context.max_output_size > 0:
            if check_device_output_limit(
                context.headers.get("device-id"), context.max_output_size
            ):
                await self._max_out_size(context, transport)
                return

        if context.is_speaking and getattr(context, "listen_mode", "auto") != "manual":
            await self._handle_abort_message(context, transport)

        context.abort_requested = False
        if not preserve_close_after_chat:
            context.close_after_chat = False

        # 首先进行意图分析，使用实际文本内容
        from core.processors.chat_processor import ChatProcessor
        chat_processor = ChatProcessor()
        intent_handled = await chat_processor.handle_user_intent(context, transport, actual_text)

        if intent_handled:
            # 如果意图已被处理，不再进行聊天
            return

        # 意图未被处理，继续常规聊天流程，使用实际文本内容
        await self._send_stt_message(context, transport, actual_text)

        # 与旧架构一致：将聊天处理放入线程池，避免阻塞事件循环
        from core.processors.chat_processor import ChatProcessor
        chat_processor = ChatProcessor()

        if hasattr(context, "create_background_task"):
            context.create_background_task(
                chat_processor.handle_chat(
                    context,
                    transport,
                    actual_text,
                    skip_intent=True,
                ),
                turn_scoped=True,
            )
        else:
            await chat_processor.handle_chat(
                context, transport, actual_text, skip_intent=True
            )

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
                    if transport.keeps_connection_between_sessions:
                        session_id = context.session_id
                        end_conversation = getattr(context, "end_conversation", None)
                        if callable(end_conversation):
                            await end_conversation(session_id)
                        await transport.end_session(session_id)
                        context.close_after_chat = False
                        context.reset_vad_states()
                    else:
                        await transport.close()
                    return

                prompt = end_prompt.get("prompt")
                if not prompt:
                    prompt = "请你以```时间过得真快```未来头，用富有感情、依依不舍的话来结束这场对话吧。！"
                await self.start_to_chat(
                    context,
                    transport,
                    prompt,
                    preserve_close_after_chat=True,
                )

    async def _max_out_size(self, context: SessionContext, transport: TransportInterface):
        """超出最大输出字数处理 - 完整迁移自max_out_size"""
        # 播放超出最大输出字数的提示
        context.abort_requested = False
        text = "不好意思，我现在有点事情要忙，明天这个时候我们再聊，约好了哦！明天不见不散，拜拜！"
        await self._send_stt_message(context, transport, text)

        file_path = "config/assets/max_output_size.wav"
        opus_packets = await audio_to_data(file_path)

        # 获取TTS组件并添加到队列
        tts_component = await self._get_component(context, ComponentType.TTS)
        if tts_component and hasattr(tts_component, 'tts_instance'):
            tts_instance = tts_component.tts_instance
            if hasattr(tts_instance, 'tts_audio_queue'):
                from core.providers.tts.dto.dto import SentenceType
                tts_instance.tts_audio_queue.put(
                    (SentenceType.LAST, opus_packets, text, context.sentence_id)
                )

        context.close_after_chat = True

    async def prompt_bind_device(
        self,
        context: SessionContext,
        transport: TransportInterface,
    ):
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
            tts_component = await self._get_component(context, ComponentType.TTS)
            if not tts_component or not hasattr(tts_component, 'tts_instance'):
                return

            tts_instance = tts_component.tts_instance
            if not hasattr(tts_instance, 'tts_audio_queue'):
                return

            # 播放提示音
            from core.providers.tts.dto.dto import SentenceType
            music_path = "config/assets/bind_code.wav"
            opus_packets = await audio_to_data(music_path)
            tts_instance.tts_audio_queue.put(
                (SentenceType.FIRST, opus_packets, text, context.sentence_id)
            )

            # 逐个播放数字
            for i in range(6):  # 确保只播放6位数字
                try:
                    digit = bind_code[i]
                    num_path = f"config/assets/bind_code/{digit}.wav"
                    num_packets = await audio_to_data(num_path)
                    tts_instance.tts_audio_queue.put(
                        (SentenceType.MIDDLE, num_packets, None, context.sentence_id)
                    )
                except Exception as e:
                    logger.error(f"播放数字音频失败: {e}")
                    continue
            tts_instance.tts_audio_queue.put(
                (SentenceType.LAST, [], None, context.sentence_id)
            )
        else:
            # 播放未绑定提示
            context.abort_requested = False
            text = f"没有找到该设备的版本信息，请正确配置 OTA地址，然后重新编译固件。"
            await self._send_stt_message(context, transport, text)

            # 获取TTS组件
            tts_component = await self._get_component(context, ComponentType.TTS)
            if tts_component and hasattr(tts_component, 'tts_instance'):
                tts_instance = tts_component.tts_instance
                if hasattr(tts_instance, 'tts_audio_queue'):
                    from core.providers.tts.dto.dto import SentenceType
                    music_path = "config/assets/bind_not_found.wav"
                    opus_packets = await audio_to_data(music_path)
                    tts_instance.tts_audio_queue.put(
                        (SentenceType.LAST, opus_packets, text, context.sentence_id)
                    )

    async def _handle_abort_message(self, context: SessionContext, transport: TransportInterface):
        """处理中断消息"""
        from core.processors.abort_processor import AbortProcessor

        await AbortProcessor().handle_abort_message(
            context,
            transport,
            {"type": "abort", "session_id": context.session_id},
        )

    async def _clear_queues(self, context: SessionContext):
        """清理所有队列"""
        # 清理TTS音频队列
        tts_component = await self._get_component(context, ComponentType.TTS)
        if tts_component and hasattr(tts_component, 'tts_instance'):
            tts_instance = tts_component.tts_instance
            for queue_name in ('tts_text_queue', 'tts_audio_queue'):
                pending_queue = getattr(tts_instance, queue_name, None)
                if pending_queue is None:
                    continue
                try:
                    while not pending_queue.empty():
                        pending_queue.get_nowait()
                except Exception:
                    pass

        # Invalidate late TTS text/audio generated by the interrupted turn.
        context.sentence_id = uuid.uuid4().hex

        # 清理ASR音频队列
        context.clear_audio_buffer()

    async def _get_component(self, context: SessionContext, component_type: ComponentType):
        if not context.component_manager:
            return None
        return await context.component_manager.get_component(component_type, context)

    async def _send_stt_message(self, context: SessionContext, transport: TransportInterface, text: str):
        """发送STT消息"""
        from core.processors.audio_send_processor import AudioSendProcessor

        await AudioSendProcessor().send_stt_message(
            context, transport, text
        )
