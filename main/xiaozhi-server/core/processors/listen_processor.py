import time
import json
import asyncio
import uuid
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.utils.util import remove_punctuation_and_length
from core.utils.dialogue import Message
from core.components.component_manager import ComponentType
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from core.processors.audio_receive_processor import arm_wake_audio_suppression
from config.logger import setup_logging

logger = setup_logging()


class ListenProcessor(MessageProcessor):
    """Listen消息处理器：完整迁移listenMessageHandler.py的所有功能"""

    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理listen类型的消息"""
        msg_json = None
        if isinstance(message, str):
            try:
                msg_json = json.loads(message)
            except json.JSONDecodeError:
                msg_json = None
        elif isinstance(message, dict):
            msg_json = message

        if isinstance(msg_json, dict) and msg_json.get("type") == "listen":
            await self.handle_listen_message(context, transport, msg_json)
            return True
        return False

    async def handle_listen_message(self, context: SessionContext, transport: TransportInterface, msg_json: dict):
        """处理listen消息 - 完整迁移自listenMessageHandler.py"""
        msg_session_id = msg_json.get("session_id")
        if msg_session_id and msg_session_id != context.session_id:
            logger.warning(
                f"忽略非当前会话的listen消息: "
                f"msg={msg_session_id}, current={context.session_id}"
            )
            return

        state = msg_json.get("state")
        has_datagram_audio = getattr(
            transport, "has_datagram_audio", False
        )
        if (
            has_datagram_audio
            and state in {"start", "detect"}
            and not context.conversation_active
        ):
            if transport.keeps_connection_between_sessions:
                await transport.send_json(
                    {
                        "type": "goodbye",
                        "session_id": msg_session_id or context.session_id,
                    }
                )
            logger.info(
                "忽略已结束会话的listen {}: session_id={}",
                state,
                context.session_id,
            )
            return

        # 设置拾音模式
        if "mode" in msg_json:
            context.listen_mode = msg_json["mode"]
            logger.debug(f"客户端拾音模式：{context.listen_mode}")

        # 处理不同的状态
        if state == "start":
            pending_start = getattr(context, "listen_start_task", None)
            if pending_start and not pending_start.done():
                logger.debug("忽略尾包隔离期内的重复listen start")
                return
            tail_quarantine = await self._flush_pending_listen_stop(
                context, transport
            )
            # 开始监听语音
            logger.info(f"listen start: session_id={context.session_id}, mode={context.listen_mode}")
            context.reset_audio_states()
            if (
                getattr(transport, "requires_audio_tail_grace", False)
                and tail_quarantine > 0
            ):
                context.accepting_input_audio = False
                context.listen_start_task = context.create_background_task(
                    self._open_input_after_tail_quarantine(
                        context,
                        context.session_id,
                        tail_quarantine,
                    ),
                    turn_scoped=True,
                )
            else:
                context.accepting_input_audio = True
            context.abort_requested = False
            context.close_after_chat = False
            logger.debug("开始语音监听")

        elif state == "stop":
            # 停止监听语音
            logger.info(f"listen stop: session_id={context.session_id}")
            context.client_have_voice = True
            context.listen_stop_pending = True
            pending_start = getattr(context, "listen_start_task", None)
            if pending_start and not pending_start.done():
                pending_start.cancel()
            context.listen_start_task = None

            if getattr(transport, "requires_audio_tail_grace", False):
                pending = getattr(context, "listen_stop_task", None)
                if pending and not pending.done():
                    logger.debug("忽略重复的listen stop")
                    return
                delay_ms = max(
                    0,
                    min(
                        1000,
                        int(
                            context.config.get(
                                "mqtt_udp_tail_grace_ms", 180
                            )
                        ),
                    ),
                )
                context.listen_stop_deadline = (
                    time.monotonic() + delay_ms / 1000
                )
                context.listen_stop_task = context.create_background_task(
                    self._finalize_listen_stop(
                        context,
                        transport,
                        context.session_id,
                        delay_ms / 1000,
                    ),
                    turn_scoped=True,
                )
            else:
                context.listen_stop_deadline = 0.0
                await self._finalize_listen_stop(
                    context,
                    transport,
                    context.session_id,
                    0,
                )
            logger.debug("停止语音监听")

        elif state == "detect":
            # 检测到文本输入
            logger.info(f"listen detect: session_id={context.session_id}, text={msg_json.get('text')}")
            context.client_have_voice = False
            context.asr_audio.clear()

            if "text" in msg_json:
                context.update_activity()
                original_text = msg_json["text"]  # 保留原始文本
                filtered_len, filtered_text = remove_punctuation_and_length(original_text)

                if original_text.startswith("[device_call]"):
                    await self._handle_device_call(
                        context,
                        transport,
                        original_text[len("[device_call]"):].strip(),
                    )
                    return

                # 识别是否是唤醒词
                is_wakeup_words = filtered_text in context.config.get("wakeup_words", [])
                # 是否开启唤醒词回复
                enable_greeting = context.config.get("enable_greeting", True)

                if is_wakeup_words and not enable_greeting:
                    # 如果是唤醒词，且关闭了唤醒词回复，就不用回答
                    # Native already drops wake history until listen/start.
                    # Keeping the greeting suppression window armed here would
                    # discard the beginning of the user's first real utterance.
                    await self._send_stt_message(context, transport, original_text)
                    await self._send_tts_message(context, transport, "stop", None)
                    context.is_speaking = False

                elif is_wakeup_words:
                    # 处理唤醒词
                    self._arm_wake_audio_suppression(context)
                    # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                    await self._enqueue_asr_report(context, "嘿，你好呀", [])
                    await self._start_to_chat(context, transport, "嘿，你好呀", skip_intent=True)

                else:
                    # 处理普通文本
                    # 上报纯文字数据（复用ASR上报功能，但不提供音频数据）
                    await self._enqueue_asr_report(context, original_text, [])
                    # 否则需要LLM对文字内容进行答复
                    await self._start_to_chat(context, transport, original_text)

    async def _flush_pending_listen_stop(
        self,
        context: SessionContext,
        transport: TransportInterface,
    ) -> float:
        """Finalize buffered speech before a new listen/start resets the turn."""
        pending = getattr(context, "listen_stop_task", None)
        had_pending_stop = bool(getattr(context, "listen_stop_pending", False))
        tail_quarantine = max(
            0.0,
            float(getattr(context, "listen_stop_deadline", 0.0) or 0.0)
            - time.monotonic(),
        )
        if pending and not pending.done():
            pending.cancel()
            try:
                await pending
            except asyncio.CancelledError:
                pass
        context.listen_stop_task = None
        if had_pending_stop:
            await self._finalize_listen_stop(
                context,
                transport,
                context.session_id,
                0,
            )
        else:
            context.listen_stop_pending = False
        if tail_quarantine <= 0:
            context.listen_stop_deadline = 0.0
        return tail_quarantine

    @staticmethod
    async def _open_input_after_tail_quarantine(
        context: SessionContext,
        session_id: str,
        delay_seconds: float,
    ) -> None:
        current_task = asyncio.current_task()
        try:
            await asyncio.sleep(delay_seconds)
            if (
                context.session_id == session_id
                and context.conversation_active
                and not context.listen_stop_pending
            ):
                context.accepting_input_audio = True
        finally:
            if getattr(context, "listen_start_task", None) is current_task:
                context.listen_start_task = None
                context.listen_stop_deadline = 0.0

    async def _finalize_listen_stop(
        self,
        context: SessionContext,
        transport: TransportInterface,
        session_id: str,
        delay_seconds: float,
    ) -> None:
        """Finalize ASR after datagram tail frames have crossed the router."""
        current_task = asyncio.current_task()
        try:
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            if context.session_id != session_id:
                return
            if (
                getattr(transport, "has_datagram_audio", False)
                and not context.conversation_active
            ):
                return

            # Close the tail-grace ingress gate before resolving ASR.
            # Component lookup may fail; leaving it open would leak subsequent
            # packets into a turn that has already stopped.
            context.listen_stop_pending = False
            context.client_voice_stop = True
            if getattr(transport, "requires_audio_tail_grace", False):
                context.accepting_input_audio = False

            asr_component = await self._get_component(
                context, ComponentType.ASR
            )
            if context.session_id != session_id:
                return
            asr_instance = (
                getattr(asr_component, "asr_instance", None)
                if asr_component
                else None
            )

            if not asr_instance or not hasattr(
                asr_instance, "interface_type"
            ):
                return

            from core.providers.asr.dto.dto import InterfaceType

            if asr_instance.interface_type == InterfaceType.STREAM:
                if hasattr(asr_instance, "_send_stop_request"):
                    await asr_instance._send_stop_request()
                return

            if context.asr_audio:
                asr_audio_task = context.asr_audio.copy()
                context.asr_audio.clear()
                context.reset_vad_states()
                await asr_instance.handle_voice_stop(
                    context, asr_audio_task
                )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.error(
                "listen stop收尾失败: session_id={}, error={}",
                session_id,
                error,
            )
        finally:
            if getattr(context, "listen_stop_task", None) is current_task:
                context.listen_stop_task = None
                context.listen_stop_deadline = 0.0
            if context.session_id == session_id:
                context.listen_stop_pending = False
                if getattr(transport, "requires_audio_tail_grace", False):
                    context.accepting_input_audio = False

    def _arm_wake_audio_suppression(self, context: SessionContext) -> None:
        """Bound the UDP/TCP reorder window used by the legacy gateway flow."""
        arm_wake_audio_suppression(context)

    async def _handle_device_call(
        self,
        context: SessionContext,
        transport: TransportInterface,
        call_text: str,
    ) -> None:
        """Restore the legacy device-call announcement and call-state handoff."""
        logger.info(f"收到设备呼叫指令: {call_text}")
        context.incoming_call = True
        context.sentence_id = uuid.uuid4().hex
        await self._send_stt_message(context, transport, call_text)

        tts_component = await self._get_component(context, ComponentType.TTS)
        tts_instance = (
            getattr(tts_component, "tts_instance", None)
            if tts_component
            else None
        )
        if tts_instance:
            tts_instance.store_tts_text(context.sentence_id, call_text)
            tts_instance.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=context.sentence_id,
                    sentence_type=SentenceType.FIRST,
                    content_type=ContentType.ACTION,
                )
            )
            tts_instance.tts_one_sentence(
                context,
                ContentType.TEXT,
                content_detail=call_text,
            )
            tts_instance.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=context.sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )

        context.dialogue.put(Message(role="assistant", content=call_text))

    async def _handle_audio_message(self, context: SessionContext, transport: TransportInterface, audio: bytes):
        """处理音频消息 - 调用AudioReceiveProcessor"""
        # 这里应该调用AudioReceiveProcessor来处理音频
        from core.processors.audio_receive_processor import AudioReceiveProcessor
        audio_processor = AudioReceiveProcessor()
        await audio_processor.handle_audio_message(context, transport, audio)

    async def _send_stt_message(self, context: SessionContext, transport: TransportInterface, text: str):
        """发送STT消息"""
        from core.processors.audio_send_processor import AudioSendProcessor

        await AudioSendProcessor().send_stt_message(
            context, transport, text
        )

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

    async def _get_component(self, context: SessionContext, component_type: ComponentType):
        if not context.component_manager:
            return None
        return await context.component_manager.get_component(component_type, context)

    async def _enqueue_asr_report(self, context: SessionContext, text: str, audio_data: list):
        """ASR上报队列"""
        if context.report_asr_enable:
            from core.processors.report_processor import ReportProcessor
            report_processor = ReportProcessor()
            report_processor.enqueue_asr_report(context, text, audio_data)

    async def _start_to_chat(self, context: SessionContext, transport: TransportInterface, text: str, skip_intent: bool = False):
        """开始聊天 - 调用ChatProcessor"""
        # 与旧架构一致：先发送STT，再异步触发聊天，避免阻塞事件循环
        await self._send_stt_message(context, transport, text)

        from core.processors.chat_processor import ChatProcessor
        chat_processor = ChatProcessor()

        if hasattr(context, "create_background_task"):
            context.create_background_task(
                chat_processor.handle_chat(
                    context, transport, text, skip_intent=skip_intent
                ),
                turn_scoped=True,
            )
            logger.info(f"chat任务已提交: session_id={context.session_id}")
        else:
            await chat_processor.handle_chat(context, transport, text, skip_intent=skip_intent)
