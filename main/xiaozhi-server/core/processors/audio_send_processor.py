import asyncio
import json
import time
from typing import Any, List
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.providers.tts.dto.dto import SentenceType
from core.utils import textUtils
from core.components.component_manager import ComponentType
from core.services.audio_ingress_service import AudioIngressService
from config.logger import setup_logging

logger = setup_logging()


class AudioSendProcessor(MessageProcessor):
    """音频发送处理器：完整迁移sendAudioHandle.py的所有功能"""

    def __init__(self, audio_ingress_service=None):
        self.audio_ingress_service = audio_ingress_service or AudioIngressService()

    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """这个处理器不直接处理消息，而是被其他处理器调用"""
        return False

    async def send_audio_message(self, context: SessionContext, transport: TransportInterface,
                                sentence_type: SentenceType, audios: bytes, text: str,
                                sentence_id: str = None):
        """发送音频消息 - 完整迁移自sendAudioMessage"""
        if not self._is_current_turn(context, sentence_id):
            return

        tts_component = await self._get_component(context, ComponentType.TTS)
        if not tts_component or not hasattr(tts_component, 'tts_instance'):
            return

        tts_instance = tts_component.tts_instance

        if hasattr(tts_instance, 'tts_audio_first_sentence') and tts_instance.tts_audio_first_sentence:
            logger.info(f"发送第一段语音: {text}")
            tts_instance.tts_audio_first_sentence = False
            await self.start_tts_stream(context, transport)

        if sentence_type == SentenceType.FIRST:
            await self.send_tts_message(
                context, transport, "sentence_start", text, sentence_id=sentence_id
            )

        await self.send_audio(
            context, transport, audios, sentence_id=sentence_id
        )
        if not self._is_current_turn(context, sentence_id):
            return

        # 发送句子开始消息
        if sentence_type is not SentenceType.MIDDLE:
            logger.info(f"发送音频消息: {sentence_type}, {text}")

        # 发送结束消息（如果是最后一个文本）
        if (
            not getattr(context, "calling", False)
            and context.llm_finish_task
            and sentence_type == SentenceType.LAST
        ):
            # Latch the terminal action before sending tts:stop. The device can
            # immediately answer with listen:start, whose handler resets the
            # mutable turn flags while this coroutine is still awaiting I/O.
            close_after_chat = bool(context.close_after_chat)
            closing_session_id = (
                getattr(transport, "session_id", None) or context.session_id
            )
            if close_after_chat:
                context.close_after_chat = False
            await self.send_tts_message(
                context, transport, "stop", None, sentence_id=sentence_id
            )
            if not self._is_current_turn(context, sentence_id):
                return
            context.is_speaking = False
            if close_after_chat:
                # MQTT/UDP：结束后回到Idle，不关闭连接
                if transport.keeps_connection_between_sessions:
                    end_conversation = getattr(context, "end_conversation", None)
                    if callable(end_conversation):
                        await end_conversation(closing_session_id)
                    await transport.end_session(closing_session_id)
                else:
                    await transport.close()

    async def send_audio(
        self,
        context: SessionContext,
        transport: TransportInterface,
        audios: bytes,
        frame_duration: int = 60,
        sentence_id: str = None,
    ):
        """发送单个opus包，支持流控 - 完整迁移自sendAudio"""
        if audios is None or len(audios) == 0:
            return
        if getattr(context, "audio_flow_control", {}).get("send_failed"):
            return

        # MQTT/UDP：等待UDP远端地址就绪，避免首包丢失
        if transport.has_datagram_audio:
            if not await transport.wait_audio_ready(timeout=2):
                logger.warning("UDP远端地址未就绪，跳过音频发送")
                return

        audio_list = [audios] if isinstance(audios, bytes) else audios
        if not isinstance(audio_list, list):
            return

        flow = context.audio_flow_control
        pre_buffer_count = max(
            0, int(context.config.get("tts_pre_buffer_count", 5))
        )
        for audio in audio_list:
            if context.abort_requested or not self._is_current_turn(context, sentence_id):
                break

            # Match the legacy AudioRateController contract: send only the
            # initial pre-buffer inline, then enqueue the remaining frames so
            # the TTS consumer can prefetch later sentence chunks.
            packet_count = int(flow.get("packet_count", 0))
            if packet_count < pre_buffer_count and "_send_queue" not in flow:
                sent = await self._send_audio_packet(
                    context,
                    transport,
                    flow,
                    audio,
                    frame_duration,
                    sentence_id,
                    paced=False,
                )
                if not sent:
                    break
                continue

            queue = self._ensure_audio_sender(
                context, transport, flow, sentence_id
            )
            await queue.put(("audio", audio, frame_duration, sentence_id))

    @staticmethod
    async def _pace_audio_send(
        context: SessionContext,
        frame_duration: int,
        flow: dict = None,
    ) -> None:
        flow = flow if flow is not None else context.audio_flow_control
        packet_count = int(flow.get("packet_count", 0))
        pre_buffer_count = max(0, int(context.config.get("tts_pre_buffer_count", 5)))
        if packet_count < pre_buffer_count:
            return

        configured_delay = int(context.config.get("tts_audio_send_delay", -1))
        if configured_delay > 0:
            await asyncio.sleep(configured_delay / 1000.0)
            return

        delay_ms = max(0, int(frame_duration))
        if delay_ms <= 0:
            return

        now = time.monotonic()
        # packet_count is the number already sent. The first packet after the
        # pre-buffer must therefore wait one complete frame, not become an
        # extra immediate packet.
        paced_packet_index = packet_count - pre_buffer_count + 1
        pacing_started_at = flow.get("pacing_started_at")
        pacing_delay_ms = flow.get("pacing_delay_ms")
        if pacing_started_at is None or pacing_delay_ms != delay_ms:
            pacing_started_at = now
            flow["pacing_started_at"] = pacing_started_at
            flow["pacing_delay_ms"] = delay_ms

        delay_seconds = delay_ms / 1000.0
        target = pacing_started_at + paced_packet_index * delay_seconds

        # TTS producers can pause between sentence chunks. Rebase after a
        # full-frame gap instead of bursting stale deadlines to catch up.
        if now - target >= delay_seconds:
            pacing_started_at = now - paced_packet_index * delay_seconds
            flow["pacing_started_at"] = pacing_started_at
            target = now

        wait_seconds = target - now
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

    def _ensure_audio_sender(
        self,
        context: SessionContext,
        transport: TransportInterface,
        flow: dict,
        sentence_id: str = None,
    ) -> asyncio.Queue:
        queue = flow.get("_send_queue")
        task = flow.get("_send_task")
        if queue is not None and task is not None and not task.done():
            return queue

        queue_size = max(
            1, int(context.config.get("tts_audio_queue_size", 256))
        )
        queue = asyncio.Queue(maxsize=queue_size)
        sender = self._audio_send_loop(
            context, transport, flow, queue, sentence_id
        )
        create_task = getattr(context, "create_background_task", None)
        if callable(create_task):
            task = create_task(sender, turn_scoped=True)
        else:
            task = asyncio.create_task(sender)
        flow["_send_queue"] = queue
        flow["_send_task"] = task
        return queue

    async def _audio_send_loop(
        self,
        context: SessionContext,
        transport: TransportInterface,
        flow: dict,
        queue: asyncio.Queue,
        sentence_id: str = None,
    ) -> None:
        try:
            while True:
                item = await queue.get()
                try:
                    item_type = item[0]
                    if not self._is_current_turn(context, sentence_id):
                        continue
                    if item_type == "audio":
                        _, audio, frame_duration, item_sentence_id = item
                        await self._send_audio_packet(
                            context,
                            transport,
                            flow,
                            audio,
                            frame_duration,
                            item_sentence_id,
                            paced=True,
                        )
                    elif item_type == "json":
                        _, message, item_sentence_id = item
                        if self._is_current_turn(context, item_sentence_id):
                            await transport.send_json(message)
                finally:
                    queue.task_done()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            flow["send_failed"] = True
            logger.error("后台音频发送循环失败: {}", error)
        finally:
            while True:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                else:
                    queue.task_done()

    async def _send_audio_packet(
        self,
        context: SessionContext,
        transport: TransportInterface,
        flow: dict,
        audio: bytes,
        frame_duration: int,
        sentence_id: str = None,
        *,
        paced: bool,
    ) -> bool:
        if paced:
            await self._pace_audio_send(context, frame_duration, flow)
        if context.abort_requested or not self._is_current_turn(context, sentence_id):
            return False

        context.update_activity()
        timestamp = self._next_audio_timestamp(
            context, frame_duration, flow
        )
        sent = await self._send_audio_with_retry(
            context,
            transport,
            audio,
            timestamp,
            sentence_id,
            flow,
        )
        if not sent or not self._is_current_turn(context, sentence_id):
            return False
        self.audio_ingress_service.cache_output_reference(
            context, audio, timestamp
        )
        flow["packet_count"] = int(flow.get("packet_count", 0)) + 1
        return True

    async def _send_audio_with_retry(
        self,
        context: SessionContext,
        transport: TransportInterface,
        audio: bytes,
        timestamp: int,
        sentence_id: str = None,
        flow: dict = None,
    ) -> bool:
        flow = flow if flow is not None else context.audio_flow_control
        retries = max(0, int(context.config.get("audio_send_retries", 2)))
        retry_delay = max(
            0, int(context.config.get("audio_send_retry_delay_ms", 20))
        ) / 1000.0
        for attempt in range(retries + 1):
            if context.abort_requested or not self._is_current_turn(context, sentence_id):
                return False
            try:
                await transport.send_audio(audio, timestamp)
                return self._is_current_turn(context, sentence_id)
            except Exception as error:
                if attempt >= retries:
                    flow["send_failed"] = True
                    logger.error(
                        "Audio send failed after {} attempts: {}",
                        attempt + 1,
                        error,
                    )
                    raise
                await asyncio.sleep(retry_delay)
        return False

    @staticmethod
    def _next_audio_timestamp(
        context: SessionContext,
        frame_duration: int,
        flow: dict = None,
    ) -> int:
        flow = flow if flow is not None else getattr(
            context, "audio_flow_control", None
        )
        if flow is None:
            flow = {}
            context.audio_flow_control = flow
        timestamp_step = int(frame_duration) or int(
            getattr(context, "output_frame_duration", 60) or 60
        )
        timestamp = int(flow.get("output_timestamp", 0)) + timestamp_step
        timestamp %= 2 ** 32
        flow["output_timestamp"] = timestamp
        return timestamp

    async def send_stt_message(self, context: SessionContext, transport: TransportInterface, text: str):
        """发送STT消息 - 完整迁移自send_stt_message"""
        end_prompt = getattr(context, "config", {}).get("end_prompt", {}).get("prompt")
        if end_prompt and text == end_prompt:
            await self.start_tts_stream(context, transport)
            return

        display_text = text
        parsed_data = None
        if isinstance(text, dict):
            parsed_data = text
        elif isinstance(text, str):
            stripped = text.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    parsed_data = json.loads(stripped)
                except json.JSONDecodeError:
                    pass

        if isinstance(parsed_data, dict) and "content" in parsed_data:
            display_text = parsed_data["content"]
            if "speaker" in parsed_data:
                context.current_speaker = parsed_data["speaker"]

        stt_text = textUtils.get_string_no_punctuation_or_emoji(
            str(display_text)
        )
        await self._send_json(transport, {
            "type": "stt",
            "text": stt_text,
            "session_id": context.session_id
        })
        logger.info(f"发送STT消息: {stt_text}")
        # Legacy WS sends TTS start together with STT, before synthesis begins.
        # This lead time is required by MQTT/UDP clients because the device
        # changes to Speaking asynchronously and drops UDP audio beforehand.
        await self.start_tts_stream(context, transport)

    async def start_tts_stream(
        self,
        context: SessionContext,
        transport: TransportInterface,
    ) -> bool:
        """Open one device-side TTS stream without sending duplicate starts."""
        if getattr(context, "is_speaking", False):
            return False

        context.is_speaking = True
        flow_control = getattr(context, "audio_flow_control", None) or {}
        await self._stop_audio_sender(flow_control)
        context.audio_flow_control = {}
        try:
            await self._send_json(transport, {
                "type": "tts",
                "state": "start",
                "session_id": context.session_id,
            })
        except Exception:
            context.is_speaking = False
            raise
        return True

    @staticmethod
    async def _send_json(
        transport: TransportInterface,
        message: dict,
    ) -> None:
        send_json = getattr(transport, "send_json", None)
        if callable(send_json):
            await send_json(message)
            return
        await transport.send(json.dumps(message))

    async def send_tts_message(
        self,
        context: SessionContext,
        transport: TransportInterface,
        state: str,
        text: str = None,
        sentence_id: str = None,
    ):
        """发送TTS消息 - 完整迁移自send_tts_message"""
        if not self._is_current_turn(context, sentence_id):
            return False
        if state == "sentence_start":
            flow = getattr(context, "audio_flow_control", {})
            queue = flow.get("_send_queue")
            task = flow.get("_send_task")
            if queue is not None and task is not None and not task.done():
                message = {
                    "type": "tts",
                    "state": state,
                    "session_id": context.session_id,
                }
                if text:
                    message["text"] = text
                await queue.put(("json", message, sentence_id))
                return True
        if state == "stop":
            if context.config.get("enable_stop_tts_notify", False):
                from core.utils.util import audio_to_data

                notify_path = context.config.get(
                    "stop_tts_notify_voice", "config/assets/tts_notify.mp3"
                )
                notify_audio = await audio_to_data(notify_path, is_opus=True)
                if notify_audio:
                    await self.send_audio(
                        context,
                        transport,
                        notify_audio,
                        sentence_id=sentence_id,
                    )
            if not await self._wait_for_audio_completion(context, sentence_id):
                return False

        if not self._is_current_turn(context, sentence_id):
            return False

        message = {
            "type": "tts",
            "state": state,
            "session_id": context.session_id
        }
        if text:
            message["text"] = text

        await transport.send_json(message)
        logger.debug(f"发送TTS消息: state={state}, text={text}")
        return True

    @staticmethod
    async def _wait_for_audio_completion(
        context: SessionContext, sentence_id: str = None
    ) -> bool:
        flow = context.audio_flow_control
        queue = flow.get("_send_queue")
        sender_task = flow.get("_send_task")
        if queue is not None and sender_task is not None:
            join_task = asyncio.create_task(queue.join())
            done, _ = await asyncio.wait(
                {join_task, sender_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if sender_task in done and not join_task.done():
                join_task.cancel()
                await asyncio.gather(join_task, return_exceptions=True)
                return False
            await join_task
            await AudioSendProcessor._stop_audio_sender(flow)
        if flow.get("send_failed"):
            return False

        packet_count = int(flow.get("packet_count", 0))
        if packet_count <= 0:
            return AudioSendProcessor._is_current_turn(context, sentence_id)
        frame_duration = max(1, int(getattr(context, "output_frame_duration", 60)))
        pre_buffer_count = max(0, int(context.config.get("tts_pre_buffer_count", 5)))
        tail_frames = max(
            0,
            int(context.config.get("tts_stop_buffer_frames", pre_buffer_count + 2)),
        )
        if tail_frames:
            await asyncio.sleep(tail_frames * frame_duration / 1000.0)
        return AudioSendProcessor._is_current_turn(context, sentence_id)

    @staticmethod
    async def _stop_audio_sender(flow: dict) -> None:
        task = flow.pop("_send_task", None)
        flow.pop("_send_queue", None)
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    @staticmethod
    def _is_current_turn(context: SessionContext, sentence_id: str = None) -> bool:
        if sentence_id is None:
            return bool(
                getattr(context, "conversation_active", True)
                and getattr(context, "sentence_id", None) is None
            )
        return sentence_id == context.sentence_id

    async def send_music_message(self, context: SessionContext, transport: TransportInterface,
                                music_path: str, text: str):
        """发送音乐消息 - 完整迁移自send_music_message"""
        from core.utils.util import audio_to_data

        try:
            # 获取音频数据
            opus_packets = await audio_to_data(music_path)
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

    async def _get_component(self, context: SessionContext, component_type: ComponentType):
        if not context.component_manager:
            return None
        return await context.component_manager.get_component(component_type, context)

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
