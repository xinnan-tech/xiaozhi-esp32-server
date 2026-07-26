import time
import json
import random
import asyncio
import uuid
from typing import Any
from core.pipeline.message_pipeline import MessageProcessor
from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.utils.dialogue import Message
from core.utils.util import audio_to_data, remove_punctuation_and_length, opus_datas_to_wav_bytes
from core.providers.tts.dto.dto import SentenceType
from core.processors.audio_receive_processor import arm_wake_audio_suppression
from core.utils.wakeup_word import WakeupWordsConfig
from core.components.component_manager import ComponentType
from core.providers.tools.device_mcp import (
    MCPClient,
    send_mcp_initialize_message,
)
from config.logger import setup_logging

logger = setup_logging()

# 唤醒词配置
WAKEUP_CONFIG = {
    "refresh_time": 5,
    "words": ["你好", "你好啊", "嘿，你好", "嗨"],
}

# 创建全局的唤醒词配置管理器
wakeup_words_config = WakeupWordsConfig()

# 用于防止并发调用wakeupWordsResponse的锁
_wakeup_response_lock = asyncio.Lock()


class HelloProcessor(MessageProcessor):
    """Hello消息处理器：完整迁移helloHandle.py的所有功能"""

    async def process(self, context: SessionContext, transport: TransportInterface, message: Any) -> bool:
        """处理hello类型的消息"""
        msg_json = None
        if isinstance(message, str):
            try:
                msg_json = json.loads(message)
            except json.JSONDecodeError:
                msg_json = None
        elif isinstance(message, dict):
            msg_json = message

        if isinstance(msg_json, dict) and msg_json.get("type") == "hello":
            await self.handle_hello_message(context, transport, msg_json)
            return True
        return False

    async def handle_hello_message(self, context: SessionContext, transport: TransportInterface, msg_json: dict):
        """处理hello消息 - 完整迁移自handleHelloMessage"""
        pending_tasks = []
        for task_name in (
            "listen_stop_task",
            "listen_start_task",
        ):
            pending_task = getattr(context, task_name, None)
            if pending_task and not pending_task.done():
                pending_task.cancel()
                pending_tasks.append(pending_task)
            setattr(context, task_name, None)
        if pending_tasks:
            await asyncio.gather(*pending_tasks, return_exceptions=True)

        transport_session_id = getattr(transport, "session_id", None)
        if transport_session_id:
            if (
                context.session_id != transport_session_id
                and callable(getattr(context, "end_conversation", None))
            ):
                # A previous finalizer may already have published
                # conversation_active=False while persistence is still in
                # progress. Always join it before exposing the new session.
                await context.end_conversation(context.session_id)
            context.session_id = transport_session_id
            if context.welcome_msg:
                context.welcome_msg["session_id"] = context.session_id
        dialogue = getattr(context, "dialogue", None)
        if getattr(context, "prompt", None) and dialogue and not dialogue.dialogue:
            dialogue.update_system_message(context.prompt)
        inject_fewshot = getattr(context, "inject_tool_call_fewshot", None)
        if callable(inject_fewshot):
            inject_fewshot()
        context.conversation_active = True
        context.listen_stop_pending = False
        context.listen_stop_deadline = 0.0
        if transport.requires_audio_tail_grace:
            context.accepting_input_audio = False

        # 处理音频参数
        audio_params = msg_json.get("audio_params")
        if audio_params:
            format = audio_params.get("format")
            logger.info(f"客户端音频格式: {format}")
            context.audio_format = format
            context.input_sample_rate = int(
                audio_params.get("sample_rate", getattr(context, "input_sample_rate", 16000))
            )
            context.input_channels = int(
                audio_params.get("channels", getattr(context, "input_channels", 1))
            )
            context.input_frame_duration = int(
                audio_params.get(
                    "frame_duration", getattr(context, "input_frame_duration", 60)
                )
            )

        # 处理客户端特性
        features = msg_json.get("features") or {}
        context.features = dict(features)
        context.client_aec = bool(features.get("aec"))
        mcp_enabled = bool(features.get("mcp"))
        previous_mcp_client = getattr(context, "mcp_client", None)
        if not mcp_enabled and previous_mcp_client:
            initialize_task = getattr(
                context, "mcp_initialize_task", None
            )
            if initialize_task and not initialize_task.done():
                initialize_task.cancel()
                await asyncio.gather(
                    initialize_task, return_exceptions=True
                )
            context.mcp_initialize_task = None
            previous_mcp_cleanup = getattr(
                context, "_mcp_cleanup_callback", None
            )
            if previous_mcp_cleanup:
                context.unregister_cleanup(previous_mcp_cleanup)
                context._mcp_cleanup_callback = None
            if hasattr(previous_mcp_client, "close"):
                await previous_mcp_client.close()
            context.mcp_client = None
        if features:
            logger.info(f"客户端特性: {features}")
            if mcp_enabled:
                logger.info("客户端支持MCP")
                if context.mcp_client is None:
                    context.mcp_client = MCPClient()
                    context._mcp_cleanup_callback = (
                        context.mcp_client.close
                    )
                    context.register_cleanup(
                        context._mcp_cleanup_callback
                    )
                initialize_task = getattr(
                    context, "mcp_initialize_task", None
                )
                if (
                    not await context.mcp_client.is_ready()
                    and (
                        initialize_task is None
                        or initialize_task.done()
                    )
                ):
                    context.mcp_initialize_task = (
                        context.create_background_task(
                            send_mcp_initialize_message(
                                context, transport
                            ),
                            conversation_scoped=False,
                        )
                    )
            if features.get("aec"):
                logger.info("客户端启用了服务端AEC")

        # MQTT/UDP 场景已由MQTT连接层发送hello回复，避免重复发送websocket格式
        if transport.has_datagram_audio:
            return

        # 发送欢迎消息
        if context.welcome_msg:
            await transport.send_json(context.welcome_msg)
        else:
            # 默认欢迎消息
            welcome_msg = {
                "type": "hello",
                "session_id": context.session_id,
                "version": 1,
                "transport": "websocket"
            }
            await transport.send_json(welcome_msg)

    async def check_wakeup_words(self, context: SessionContext, transport: TransportInterface, text: str) -> bool:
        """检查唤醒词 - 完整迁移自checkWakeupWords"""
        enable_wakeup_words_response_cache = context.config.get("enable_wakeup_words_response_cache", False)

        # 等待tts初始化，最多等待3秒
        tts_component = await self._get_component(context, ComponentType.TTS)
        start_time = time.time()
        while time.time() - start_time < 3:
            if tts_component and hasattr(tts_component, 'tts_instance'):
                break
            await asyncio.sleep(0.1)
        else:
            return False

        if not enable_wakeup_words_response_cache:
            return False

        _, filtered_text = remove_punctuation_and_length(text)
        if filtered_text not in context.config.get("wakeup_words", []):
            return False

        sentence_id = uuid.uuid4().hex
        context.sentence_id = sentence_id
        context.just_woken_up = True
        await self._send_stt_message(context, transport, text)

        # 获取当前音色
        tts_instance = getattr(tts_component, 'tts_instance', None) if tts_component else None
        voice = getattr(tts_instance, "voice", "default") if tts_instance else "default"
        if not voice:
            voice = "default"

        # 获取唤醒词回复配置
        response = wakeup_words_config.get_wakeup_response(voice)
        if not response or not response.get("file_path"):
            response = {
                "voice": "default",
                "file_path": "config/assets/wakeup_words.wav",
                "time": 0,
                "text": "哈啰啊，我是小智啦，声音好听的台湾女孩一枚，超开心认识你耶，最近在忙啥，别忘了给我来点有趣的料哦，我超爱听八卦的啦",
            }

        # 获取音频数据
        opus_packets = await audio_to_data(response.get("file_path"))
        # 播放唤醒词回复
        context.abort_requested = False
        context.llm_finish_task = True
        if tts_instance is not None:
            # A prior turn may have consumed the one-shot start marker. Cached
            # playback is a new TTS stream and must always emit start first.
            tts_instance.tts_audio_first_sentence = True

        logger.info(f"播放唤醒词回复: {response.get('text')}")
        try:
            await self._send_audio_message(
                context,
                transport,
                SentenceType.FIRST,
                opus_packets,
                response.get("text"),
                sentence_id,
            )
            await self._send_audio_message(
                context,
                transport,
                SentenceType.LAST,
                [],
                None,
                sentence_id,
            )
        finally:
            # Cached wake playback bypasses ListenProcessor, so it must arm
            # the same bounded release used by the regular wake-word path.
            arm_wake_audio_suppression(context)

        # 补充对话
        if context.dialogue:
            context.dialogue.put(Message(role="assistant", content=response.get("text")))

        # 检查是否需要更新唤醒词回复
        if time.time() - response.get("time", 0) > WAKEUP_CONFIG["refresh_time"]:
            if not _wakeup_response_lock.locked():
                context.create_background_task(
                    self._wakeup_words_response(context, transport)
                )
        return True

    async def _wakeup_words_response(self, context: SessionContext, transport: TransportInterface):
        """生成唤醒词回复 - 完整迁移自wakeupWordsResponse"""
        tts_component = await self._get_component(context, ComponentType.TTS)
        llm_component = await self._get_component(context, ComponentType.LLM)

        tts_instance = getattr(tts_component, 'tts_instance', None) if tts_component else None
        llm_instance = getattr(llm_component, 'llm_instance', None) if llm_component else None

        if not tts_instance or not llm_instance or not hasattr(llm_instance, 'response_no_stream'):
            return

        try:
            # 尝试获取锁，如果获取不到就返回
            async with _wakeup_response_lock:
                # 生成唤醒词回复
                wakeup_word = random.choice(WAKEUP_CONFIG["words"])
                question = (
                    "此刻用户正在和你说```"
                    + wakeup_word
                    + "```。\n请你根据以上用户的内容进行20-30字回复。要符合系统设置的角色情感和态度，不要像机器人一样说话。\n"
                    + "请勿对这条内容本身进行任何解释和回应，请勿返回表情符号，仅返回对用户的内容的回复。"
                )

                result = await asyncio.to_thread(
                    llm_instance.response_no_stream,
                    context.config.get("prompt", ""),
                    question,
                )
                if not result or len(result) == 0:
                    return

                # 生成TTS音频
                tts_result = await asyncio.to_thread(tts_instance.to_tts, result)
                if not tts_result:
                    return

                # 获取当前音色
                voice = getattr(tts_instance, "voice", "default")

                wav_bytes = opus_datas_to_wav_bytes(tts_result, sample_rate=16000)
                file_path = wakeup_words_config.generate_file_path(voice)
                with open(file_path, "wb") as f:
                    f.write(wav_bytes)
                # 更新配置
                wakeup_words_config.update_wakeup_response(voice, file_path, result)
        except Exception as e:
            logger.error(f"生成唤醒词回复失败: {e}")

    async def _send_stt_message(self, context: SessionContext, transport: TransportInterface, text: str):
        """发送STT消息"""
        from core.processors.audio_send_processor import AudioSendProcessor

        await AudioSendProcessor().send_stt_message(
            context, transport, text
        )

    async def _send_audio_message(self, context: SessionContext, transport: TransportInterface,
                                 sentence_type: SentenceType, audios: bytes, text: str,
                                 sentence_id: str = None):
        """发送音频消息"""
        # 这里应该调用AudioSendProcessor
        from core.processors.audio_send_processor import AudioSendProcessor
        audio_send_processor = AudioSendProcessor()
        await audio_send_processor.send_audio_message(
            context,
            transport,
            sentence_type,
            audios,
            text,
            sentence_id=sentence_id,
        )

    async def _get_component(self, context: SessionContext, component_type: ComponentType):
        if not context.component_manager:
            return None
        return await context.component_manager.get_component(component_type, context)
