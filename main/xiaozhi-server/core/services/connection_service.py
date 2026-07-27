import asyncio
import copy
import json
import re
import time
from typing import Dict, Any
from urllib.parse import parse_qs, urlparse

from core.context.session_context import SessionContext
from core.transport.transport_interface import TransportInterface
from core.components.component_registry import ComponentRegistry
from core.components.component_manager import ComponentType
from core.pipeline.message_pipeline import MessagePipeline
from core.processors.message_router import MessageRouter
from config.logger import setup_logging
from config.config_loader import get_private_config_from_api
from config.manage_api_client import (
    DeviceNotFoundException,
    DeviceBindException,
    generate_and_save_chat_title,
)
from core.utils.util import check_vad_update, check_asr_update, filter_sensitive_info
from core.utils.dialogue import Dialogue, Message
from core.utils.voiceprint_provider import VoiceprintProvider

logger = setup_logging()
TAG = __name__


class ConnectionService:
    """连接服务：统一管理连接生命周期，替代ConnectionHandler"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = setup_logging()

        # 创建统一消息路由器
        self.message_router = MessageRouter()

        # 创建消息处理管道
        self.message_pipeline = MessagePipeline()
        self._setup_pipeline()

    def _setup_pipeline(self):
        """设置消息处理管道"""
        # 使用统一的MessageRouter替代单独的processor
        self.message_pipeline.add_processor(self.message_router)

    async def handle_connection(self, transport: TransportInterface, headers: Dict[str, str]):
        """处理新连接"""
        # 创建会话上下文
        base_config = dict(self.config)
        if "_shared_asr_manager" in base_config:
            del base_config["_shared_asr_manager"]
        context = SessionContext(config=base_config)
        context.headers = headers

        # 设置transport接口
        context.transport = transport

        async def handle_asr_result(text, audio_snapshot):
            from core.processors.audio_receive_processor import AudioReceiveProcessor
            from core.processors.report_processor import ReportProcessor

            ReportProcessor().enqueue_asr_report(context, text, audio_snapshot)
            await AudioReceiveProcessor().start_to_chat(
                context, transport, text
            )

        context.asr_result_handler = handle_asr_result

        async def end_conversation(session_id=None):
            await self._finalize_conversation_session(context, session_id)

        context.end_conversation = end_conversation

        # 传入共享 ASR 管理器
        # 这使得 ASRAdapter 可以使用预加载的模型实例
        if '_shared_asr_manager' in self.config:
            context.shared_asr_manager = self.config['_shared_asr_manager']
            logger.bind(tag=TAG).debug("连接使用共享 ASR 实例")

        # 兼容性：设置websocket属性（如果transport是WebSocket）
        if transport.transport_type in ("websocket", "gateway"):
            context.websocket = transport.raw_connection

        # 绑定服务器实例（用于管理端下发动作）
        context.server = getattr(self, "server", None)

        # 初始化 welcome_msg（关键！设备需要这些信息来确定协议配置）
        # 从 config.xiaozhi 读取欢迎消息配置
        if 'xiaozhi' in self.config:
            import copy
            context.welcome_msg = copy.deepcopy(self.config['xiaozhi'])
            context.welcome_msg['session_id'] = context.session_id
        else:
            # 默认欢迎消息
            context.welcome_msg = {
                "type": "hello",
                "version": 1,
                "transport": "websocket",
                "session_id": context.session_id,
                "audio_params": {
                    "format": "opus",
                    "sample_rate": 16000,
                    "channels": 1,
                    "frame_duration": 60
                }
            }

        output_audio = context.welcome_msg.get("audio_params", {})
        context.output_sample_rate = int(output_audio.get("sample_rate", 24000))
        context.output_channels = int(output_audio.get("channels", 1))
        context.output_frame_duration = int(output_audio.get("frame_duration", 60))
        context.sample_rate = context.output_sample_rate
        context.channels = context.output_channels
        context.frame_duration = context.output_frame_duration

        # 从headers或URL参数中提取设备信息
        await self._extract_device_info(context, headers)
        if transport.is_protocol_authenticated:
            context.is_authenticated = True

        management_owner = context.server
        management_registered = False

        # 识别服务器管理连接（非设备连接）
        context.is_server_action_conn = self._is_server_action_connection(context, headers)

        # 创建组件管理器（仅在需要时）
        component_manager = None
        if not context.is_server_action_conn:
            component_manager = ComponentRegistry.create_component_manager(self.config)
            context.component_manager = component_manager

        # 设置绑定检查事件
        bind_completed_event = asyncio.Event()
        last_bind_prompt_time = 0
        bind_prompt_interval = 60  # 绑定提示播放间隔(秒)

        # 启动超时检查任务
        timeout_task = None
        initialization_task = None

        try:
            logger.bind(tag=TAG).info(f"新连接建立: {context.device_id} from {context.client_ip}")
            register_context = getattr(
                management_owner, "register_connection_context", None
            )
            if callable(register_context):
                try:
                    management_registered = bool(
                        await register_context(context, transport)
                    )
                except Exception as e:
                    logger.bind(tag=TAG).warning(
                        "注册连接管理上下文失败: {}", e
                    )

            if not context.is_server_action_conn:
                initialization = self._background_initialize(
                    context, component_manager, bind_completed_event
                )
                if transport.keeps_connection_between_sessions:
                    # Native MQTT owns Hello at the protocol layer. Keep its
                    # readiness barrier until the business runtime can accept
                    # the negotiated UDP session.
                    await initialization
                else:
                    # WS and Gateway clients expect the Hello response before
                    # slow Agent/provider initialization completes.
                    initialization_task = asyncio.create_task(
                        initialization,
                        name="xiaozhi-connection-initialize",
                    )
                    # Start the owner before entering receive() so immediate
                    # disconnect cleanup can still observe partial resources.
                    await asyncio.sleep(0)
            else:
                context.need_bind = False
                bind_completed_event.set()

            # Native MQTT may have received Hello while private configuration
            # was loading. Release that handshake only after the runtime can
            # consume the session boundary and subsequent audio.
            await transport.mark_business_ready()

            # 启动超时检查
            timeout_task = asyncio.create_task(self._check_timeout(context, transport))
            context.timeout_task = timeout_task

            # 处理消息流
            async for message in transport.receive():
                try:
                    msg_json = self._parse_control_message(message)
                    is_hello = (
                        isinstance(msg_json, dict)
                        and msg_json.get("type") == "hello"
                    )
                    if initialization_task is not None:
                        if is_hello and not initialization_task.done():
                            # Acknowledge transport negotiation first, then
                            # join initialization before admitting listen/audio.
                            await self.message_pipeline.process_message(
                                context, transport, message
                            )
                            await initialization_task
                            initialization_task = None

                            if getattr(context, "init_error", None):
                                await self._send_config_error_audio(
                                    context,
                                    transport,
                                    context.init_error,
                                    send_hello=False,
                                )
                                context.init_error_notified = True
                                break
                            if context.need_bind:
                                await self._prompt_bind_if_needed(
                                    context,
                                    transport,
                                    last_bind_prompt_time,
                                    bind_prompt_interval,
                                )
                                last_bind_prompt_time = time.time()
                            continue

                        await initialization_task
                        initialization_task = None

                    if getattr(context, "init_error", None):
                        # 配置错误时，允许hello/listen触发默认语音（节流）
                        msg_type = msg_json.get("type") if isinstance(msg_json, dict) else None
                        if msg_type == "hello":
                            # 配置错误场景：默认语音限流，避免唤醒循环
                            session_id = msg_json.get("session_id") if isinstance(msg_json, dict) else None
                            if session_id and session_id != context.session_id:
                                context.session_id = session_id
                            now = time.time()
                            last_audio_ts = getattr(context, "_init_error_last_audio_ts", 0.0)

                            audio_params = msg_json.get("audio_params")
                            if audio_params:
                                context.audio_format = audio_params.get("format", context.audio_format)
                            if not transport.has_datagram_audio:
                                hello_resp = {
                                    "type": "hello",
                                    "session_id": context.session_id,
                                    "version": 1,
                                    "transport": "websocket",
                                }
                                if audio_params:
                                    hello_resp["audio_params"] = audio_params
                                await transport.send_json(hello_resp)
                            # 60秒冷却：期间只发goodbye让设备回Idle，不重复播报
                            if now - last_audio_ts < 60:
                                session_id = getattr(transport, "session_id", None) or context.session_id
                                if transport.keeps_connection_between_sessions:
                                    await transport.end_session(session_id)
                            else:
                                await self._send_config_error_audio(
                                    context,
                                    transport,
                                    context.init_error,
                                    send_hello=False,
                                )
                                context.init_error_notified = True
                                context._init_error_last_audio_ts = now
                            # MQTT/UDP 连接保持，不主动断开
                            if not transport.keeps_connection_between_sessions:
                                break
                            continue
                        if getattr(context, "init_error_notified", False):
                            continue
                    # 检查绑定状态
                    should_process = await self._check_bind_status(
                        context, transport, bind_completed_event,
                        last_bind_prompt_time, bind_prompt_interval
                    )
                    if not should_process:
                        last_bind_prompt_time = time.time()
                        continue

                    await self.message_pipeline.process_message(context, transport, message)
                except Exception as e:
                    logger.bind(tag=TAG).error(f"处理消息时出错: {e}")
                    # 继续处理其他消息，不中断连接

        except Exception as e:
            logger.bind(tag=TAG).error(f"连接处理出错: {e}")
        finally:
            # 清理资源
            if management_registered:
                unregister_context = getattr(
                    management_owner, "unregister_connection_context", None
                )
                if callable(unregister_context):
                    try:
                        await unregister_context(context, transport)
                    except Exception as e:
                        logger.bind(tag=TAG).warning(
                            "注销连接管理上下文失败: {}", e
                        )

            if initialization_task and not initialization_task.done():
                initialization_task.cancel()
                await asyncio.gather(
                    initialization_task, return_exceptions=True
                )

            if timeout_task and not timeout_task.done():
                timeout_task.cancel()
                try:
                    await timeout_task
                except asyncio.CancelledError:
                    pass

            # init_task 已移除（同步初始化），这里不再取消

            await self._finalize_conversation_session(context)

            # MQTT/UDP 连接关闭前通知设备回到Idle
            try:
                if (
                    transport.keeps_connection_between_sessions
                    and transport.is_connected
                ):
                    session_id = getattr(transport, "session_id", None) or context.session_id
                    await transport.end_session(session_id)
            except Exception as e:
                logger.bind(tag=TAG).warning(f"关闭前发送goodbye失败: {e}")

            # 先停止所有生产任务和会话回调，再关闭其依赖的 Provider。
            try:
                await context.run_cleanup()
            except Exception as e:
                logger.bind(tag=TAG).error(f"会话清理失败: {e}")

            # Clean the manager currently owned by the context.
            active_component_manager = (
                getattr(context, "component_manager", None) or component_manager
            )
            if active_component_manager:
                try:
                    await active_component_manager.cleanup_all()
                except Exception as e:
                    logger.bind(tag=TAG).error(f"组件清理失败: {e}")

            try:
                await transport.close()
            except Exception as e:
                logger.bind(tag=TAG).error(f"关闭传输层失败: {e}")

            logger.bind(tag=TAG).info(f"连接已关闭: {context.device_id}")

    async def _extract_device_info(self, context: SessionContext, headers: Dict[str, str]):
        """
        从headers中提取设备信息，必要时从transport补齐
        """
        context.device_id = headers.get("device-id")
        context.headers["client-id"] = headers.get("client-id")
        context.client_ip = headers.get("x-real-ip") or headers.get("x-forwarded-for", "unknown")

        if context.client_ip and "," in context.client_ip:
            context.client_ip = context.client_ip.split(",")[0].strip()

        # MQTT连接可能在connect后才有device_id/client_id，这里等待短时间补齐
        if not context.device_id and hasattr(context.transport, "device_id"):
            for _ in range(30):
                transport_device_id = getattr(context.transport, "device_id", None)
                if transport_device_id:
                    context.device_id = transport_device_id
                    break
                await asyncio.sleep(0.1)

        if not context.device_id and hasattr(context.transport, "username"):
            transport_username = getattr(context.transport, "username", None)
            if transport_username:
                context.device_id = transport_username

        if context.device_id and not context.headers.get("device-id"):
            context.headers["device-id"] = context.device_id

        if not context.headers.get("client-id") and hasattr(context.transport, "client_id"):
            transport_client_id = getattr(context.transport, "client_id", None)
            if transport_client_id:
                context.headers["client-id"] = transport_client_id

        if (
            not context.transport.is_protocol_authenticated
            and not context.headers.get("authorization")
            and hasattr(context.transport, "password")
        ):
            transport_password = getattr(context.transport, "password", None)
            if transport_password:
                context.headers["authorization"] = transport_password

    def _is_server_action_connection(self, context: SessionContext, headers: Dict[str, str]) -> bool:
        """判断是否为管理端下发动作的临时连接"""
        if not context.read_config_from_api:
            return False
        device_id = headers.get("device-id") or ""
        if not device_id:
            return False
        # 设备ID是MAC则认为是设备连接
        mac_pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
        if re.match(mac_pattern, device_id):
            return False
        # 非MAC且带Authorization头，视为管理端连接
        return bool(headers.get("authorization"))

    async def _initialize_components(self, context: SessionContext, component_manager):
        """初始化必要的组件"""
        try:
            # 设置组件管理器到上下文
            context.component_manager = component_manager

            # 根据配置确定需要初始化的组件
            required_components = ComponentRegistry.get_required_components(context.config)
            if not required_components:
                logger.bind(tag=TAG).warning("未配置任何组件，跳过初始化")
                return

            # 按需初始化组件
            for component_type in required_components:
                component = await component_manager.get_component(component_type, context)
                if component:
                    logger.bind(tag=TAG).info(f"组件初始化成功: {component_type.value}")
                else:
                    raise RuntimeError(f"组件初始化失败: {component_type.value}")

            component_manager.lazy_enabled = False

            await self._initialize_voiceprint(context)

            # 对齐旧版：初始化意图类型与工具处理器
            selected_intent = context.config.get("selected_module", {}).get("Intent")
            intent_cfg = context.config.get("Intent", {})
            if selected_intent and selected_intent in intent_cfg:
                context.intent_type = intent_cfg[selected_intent].get("type", "nointent")
                if context.intent_type in ("function_call", "intent_llm"):
                    context.load_function_plugin = True
                    try:
                        from core.providers.tools.unified_tool_handler import UnifiedToolHandler
                        context.func_handler = UnifiedToolHandler(context)
                        context.register_cleanup(context.func_handler.cleanup)
                        await context.func_handler._initialize()
                        logger.bind(tag=TAG).info(
                            f"统一工具处理器初始化完成: intent_type={context.intent_type}"
                        )
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"初始化工具处理器失败: {e}")

            await self._initialize_prompt(context)
            context.inject_tool_call_fewshot = lambda: self._inject_tool_call_fewshot(
                context
            )
            self._inject_tool_call_fewshot(context)

        except Exception as e:
            logger.bind(tag=TAG).error(f"组件初始化出错: {e}")
            raise

    async def _initialize_voiceprint(self, context: SessionContext) -> None:
        """Initialize the connection-scoped voiceprint provider after config merge."""
        voiceprint_config = context.config.get("voiceprint") or {}
        context.voiceprint_provider = None
        if not voiceprint_config:
            logger.bind(tag=TAG).info("声纹识别功能未启用")
            return
        try:
            provider = await asyncio.to_thread(VoiceprintProvider, voiceprint_config)
            if provider.enabled:
                context.voiceprint_provider = provider
                logger.bind(tag=TAG).info("声纹识别功能已在连接时动态启用")
            else:
                logger.bind(tag=TAG).warning("声纹识别功能启用但配置不完整")
        except Exception as e:
            logger.bind(tag=TAG).warning(f"声纹识别初始化失败: {e}")

    @staticmethod
    def _inject_tool_call_fewshot(context: SessionContext) -> None:
        if context.intent_type != "function_call" or not context.func_handler:
            return
        if any(
            getattr(message, "is_temporary", False)
            for message in context.dialogue.dialogue
        ):
            return
        tools = context.func_handler.get_functions() or []
        if not tools:
            return

        tool_names = {
            tool.get("function", {}).get("name") for tool in tools
        }
        direct_id = "fewshot_da_001"
        context.dialogue.put(
            Message(role="user", content="给我讲个故事吧", is_temporary=True)
        )
        context.dialogue.put(
            Message(
                role="assistant",
                tool_calls=[
                    {
                        "id": direct_id,
                        "function": {
                            "arguments": '{"response":"好呀，你想听什么类型的呀？"}',
                            "name": "direct_answer",
                        },
                        "type": "function",
                        "index": 0,
                    }
                ],
                is_temporary=True,
            )
        )
        context.dialogue.put(
            Message(
                role="tool",
                tool_call_id=direct_id,
                content="已直接回复",
                is_temporary=True,
            )
        )

        if "handle_exit_intent" in tool_names:
            exit_id = "fewshot_exit_001"
            context.dialogue.put(
                Message(role="user", content="拜拜", is_temporary=True)
            )
            context.dialogue.put(
                Message(
                    role="assistant",
                    tool_calls=[
                        {
                            "id": exit_id,
                            "function": {
                                "arguments": '{"say_goodbye":"再见，下次再聊~"}',
                                "name": "handle_exit_intent",
                            },
                            "type": "function",
                            "index": 0,
                        }
                    ],
                    is_temporary=True,
                )
            )
            context.dialogue.put(
                Message(
                    role="tool",
                    tool_call_id=exit_id,
                    content="退出意图已处理",
                    is_temporary=True,
                )
            )
            context.dialogue.put(
                Message(
                    role="assistant",
                    content="再见，下次再聊~",
                    is_temporary=True,
                )
            )

    async def _initialize_prompt(self, context: SessionContext):
        user_prompt = context.config.get("prompt")
        if user_prompt is None or not context.prompt_manager:
            return

        quick_prompt = context.prompt_manager.get_quick_prompt(
            user_prompt, context.device_id
        )
        context.prompt = quick_prompt
        context.dialogue.update_system_message(quick_prompt)

        try:
            await asyncio.to_thread(
                context.prompt_manager.update_context_info,
                context,
                context.client_ip,
            )
            enhanced_prompt = await asyncio.to_thread(
                context.prompt_manager.build_enhanced_prompt,
                user_prompt,
                context.device_id,
                context.client_ip,
                emoji_enabled=(context.features or {}).get("emoji", True),
            )
            if enhanced_prompt:
                context.prompt = enhanced_prompt
                context.dialogue.update_system_message(enhanced_prompt)
        except Exception as e:
            logger.bind(tag=TAG).warning(f"增强系统提示词失败，使用快速提示词: {e}")

    def _collect_missing_modules(self, config: Dict[str, Any]) -> list[str]:
        selected = config.get("selected_module", {}) or {}
        missing = []
        module_keys = {
            "ASR": "语音识别",
            "LLM": "大模型",
            "TTS": "语音合成",
            "Memory": "记忆功能",
            "Intent": "意图识别",
            "VAD": "语音活动检测"
        }
        for key, name in module_keys.items():
            module_name = selected.get(key)
            if not module_name:
                missing.append(name)
                continue
            section = config.get(key, {})
            if module_name not in section:
                missing.append(name)
        return missing

    async def _send_config_error_audio(
            self,
            context: SessionContext,
            transport: TransportInterface,
            error: Exception,
            send_hello: bool = True,
    ):
        logger.bind(tag=TAG).error("配置错误，发送默认语音")
        missing = self._collect_missing_modules(context.config)
        if missing:
            missing_text = "、".join(missing)
            text = f"你好啊，很高兴认识你。在我们开始聊天之前，{missing_text}未配置完成，请前往控制台完成配置"
        else:
            text = f"配置加载失败，请前往控制台检查配置。"

        try:
            if send_hello:
                # 先发送最小 hello，避免客户端等待超时
                await transport.send_json({
                    "type": "hello",
                    "session_id": context.session_id,
                    "version": 1,
                    "transport": "websocket"
                })

            # MQTT/UDP 场景需要等待设备先发送UDP以拿到远端地址
            if transport.has_datagram_audio:
                await transport.prepare_audio_channel(
                    context.welcome_msg.get("audio_params", {}), 3
                )
                await transport.wait_audio_ready(timeout=3)

            from core.providers.tts.edge import TTSProvider as EdgeTTSProvider
            from core.utils.util import audio_bytes_to_data_stream

            # 使用 EdgeTTS 兜底提示
            tts_cfg = {
                "voice": "zh-CN-XiaoxiaoNeural",
                "format": "mp3",
                "output_dir": "tmp",
            }
            tts = EdgeTTSProvider(tts_cfg, delete_audio_file=True)
            audio_bytes = await tts.text_to_speak(text, None)
            if not audio_bytes:
                return

            # 转成 Opus 帧
            opus_frames: list[bytes] = []
            loop = asyncio.get_running_loop()

            def _convert():
                audio_bytes_to_data_stream(audio_bytes, "mp3", True, lambda f: opus_frames.append(f))

            await loop.run_in_executor(None, _convert)

            session_id = getattr(transport, "session_id", None) or context.session_id
            # 发送 TTS 状态与音频
            await transport.send_json({
                "type": "tts",
                "state": "start",
                "session_id": session_id,
            })
            await transport.send_json({
                "type": "tts",
                "state": "sentence_start",
                "text": text,
                "session_id": session_id,
            })
            for frame in opus_frames:
                await transport.send_audio(frame)
                await asyncio.sleep(0.06)
            await transport.send_json({
                "type": "tts",
                "state": "stop",
                "session_id": session_id,
            })
            # MQTT/UDP：默认语音结束后主动发送goodbye，设备回到Idle但保持MQTT连接
            if transport.keeps_connection_between_sessions:
                await transport.end_session(session_id)
            # MQTT/UDP 需要保持连接，避免发送完默认语音后断链
            if not transport.keeps_connection_between_sessions:
                await transport.close()
        except Exception as e:
            logger.bind(tag=TAG).error(f"发送配置错误提示语音失败: {e}")

    async def _background_initialize(
            self,
            context: SessionContext,
            component_manager,
            bind_completed_event: asyncio.Event
    ):
        """在后台初始化配置和组件"""
        try:
            await self._initialize_private_config(context, bind_completed_event)
            await self._initialize_components(context, component_manager)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.bind(tag=TAG).error(f"后台初始化失败: {e}")
            context.init_error = e
            # 即使初始化失败，也要设置绑定完成事件，避免消息一直被丢弃
            bind_completed_event.set()

    async def _initialize_private_config(
            self,
            context: SessionContext,
            bind_completed_event: asyncio.Event
    ):
        """从API异步获取差异化配置"""
        if not context.read_config_from_api:
            context.need_bind = False
            bind_completed_event.set()
            return

        try:
            begin_time = time.time()

            private_config = await get_private_config_from_api(
                context.config,
                context.device_id,
                context.headers.get("client-id", context.device_id),
            )

            if private_config:
                private_config["delete_audio"] = bool(context.config.get("delete_audio", True))
                logger.bind(tag=TAG).info(
                    f"{time.time() - begin_time:.2f}秒，获取差异化配置成功"
                )

                # 合并私有配置并重算所有派生字段，避免长连接刷新后残留旧值。
                self._apply_private_runtime_config(context, private_config)
                if context.component_manager is not None:
                    context.component_manager._config = context.config
                selected = context.config.get("selected_module", {})
                llm_cfg = context.config.get("LLM", {})
                logger.bind(tag=TAG).info(
                    f"私有配置模块: selected={list(selected.keys())}, LLM_selected={selected.get('LLM')}, "
                    f"LLM_keys={list(llm_cfg.keys())}"
                )

                context.need_bind = False
            else:
                context.need_bind = False

            bind_completed_event.set()

        except DeviceNotFoundException:
            logger.bind(tag=TAG).warning(f"设备 {context.device_id} 未找到，需要绑定")
            context.need_bind = True
            bind_completed_event.set()
        except DeviceBindException as e:
            logger.bind(tag=TAG).warning(f"设备绑定异常: {e}")
            context.need_bind = True
            context.bind_code = getattr(e, 'bind_code', None)
            bind_completed_event.set()
        except Exception as e:
            logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            context.need_bind = True
            bind_completed_event.set()

    @staticmethod
    def _parse_control_message(message: Any):
        if isinstance(message, dict):
            return message
        if isinstance(message, str):
            try:
                return json.loads(message)
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _reset_config_derived_state(context: SessionContext) -> None:
        """Reset fields derived from config before applying a replacement."""
        context.max_output_size = int(
            context.config.get(
                "device_max_output_size",
                context.config.get("max_output_size", 0),
            )
            or 0
        )
        context.chat_history_conf = int(
            context.config.get("chat_history_conf", 0) or 0
        )
        context.cmd_exit = list(context.config.get("exit_commands", []) or [])
        context.intent_type = "nointent"
        context.load_function_plugin = False

    def _apply_private_runtime_config(
        self, context: SessionContext, private_config: Dict[str, Any]
    ) -> None:
        """Replace common/private config and recompute connection derivatives."""
        context.config = copy.deepcopy(context.common_config)
        context.private_config = copy.deepcopy(private_config)
        self._reset_config_derived_state(context)
        applied_private_config = copy.deepcopy(private_config)
        context.config.update(applied_private_config)
        self._reset_config_derived_state(context)
        self._merge_private_modules(context, applied_private_config)

    def _merge_private_modules(self, context: SessionContext, private_config: Dict[str, Any]) -> None:
        """合并私有模块配置（与旧服务保持一致）"""
        selected = context.config.setdefault("selected_module", {})
        for module_name in ("VAD", "ASR", "TTS", "LLM", "VLLM", "Memory", "Intent"):
            module_cfg = private_config.get(module_name)
            module_selected = private_config.get("selected_module", {}).get(module_name)
            if module_cfg is not None:
                context.config[module_name] = module_cfg
            if module_selected:
                selected[module_name] = module_selected

        # 私有配置未包含VAD/ASR时，保留公共配置的选择与配置
        common_selected = context.common_config.get("selected_module", {}) if context.common_config else {}
        for module_name in ("VAD", "ASR"):
            if not selected.get(module_name) and common_selected.get(module_name):
                selected[module_name] = common_selected.get(module_name)
                if module_name not in context.config and context.common_config.get(module_name) is not None:
                    context.config[module_name] = context.common_config.get(module_name)

        # Intent插件配置处理
        intent_selected = private_config.get("selected_module", {}).get("Intent")
        if intent_selected and intent_selected != "Intent_nointent":
            plugins = private_config.get("plugins", {})
            if plugins:
                for plugin, config_str in plugins.items():
                    if isinstance(config_str, str):
                        try:
                            plugins[plugin] = json.loads(config_str)
                        except json.JSONDecodeError:
                            pass
                context.config["plugins"] = plugins
                if "Intent" in context.config and intent_selected in context.config["Intent"]:
                    context.config["Intent"][intent_selected]["functions"] = plugins.keys()

        # 更新会话级配置
        if private_config.get("device_max_output_size") is not None:
            context.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf") is not None:
            context.chat_history_conf = int(private_config["chat_history_conf"])

        # TTS providers consume replacement words from the selected module
        # configuration, matching the legacy connection runtime.
        correct_words = private_config.get("correct_words")
        selected_tts = selected.get("TTS")
        if (
            correct_words is not None
            and selected_tts
            and selected_tts in context.config.get("TTS", {})
        ):
            context.config["TTS"][selected_tts]["correct_words"] = correct_words

    async def _check_bind_status(
            self,
            context: SessionContext,
            transport: TransportInterface,
            bind_completed_event: asyncio.Event,
            last_bind_prompt_time: float,
            bind_prompt_interval: int
    ) -> bool:
        """
        检查设备绑定状态

        Returns:
            bool: True 表示可以处理消息，False 表示需要丢弃消息
        """
        # 如果还没获取到真实绑定状态，等待一下
        if not bind_completed_event.is_set():
            try:
                await asyncio.wait_for(bind_completed_event.wait(), timeout=1)
            except asyncio.TimeoutError:
                # 超时仍未获取到真实状态，丢弃消息并提示绑定
                await self._prompt_bind_if_needed(
                    context, transport, last_bind_prompt_time, bind_prompt_interval
                )
                return False

        # 检查是否需要绑定
        if context.need_bind:
            await self._prompt_bind_if_needed(
                context, transport, last_bind_prompt_time, bind_prompt_interval
            )
            return False

        return True

    async def _prompt_bind_if_needed(
            self,
            context: SessionContext,
            transport: TransportInterface,
            last_prompt_time: float,
            prompt_interval: int
    ):
        """如果需要，播放绑定提示"""
        current_time = time.time()
        if current_time - last_prompt_time >= prompt_interval:
            try:
                from core.processors.audio_receive_processor import (
                    AudioReceiveProcessor,
                )

                # Binding checks run before the normal Hello pipeline. Give the
                # prompt an explicit transport session and turn owner so the
                # TTS worker does not classify its queued audio as stale.
                transport_session_id = getattr(transport, "session_id", None)
                if transport_session_id:
                    context.session_id = transport_session_id
                context.sentence_id = (
                    f"bind:{context.session_id}:{time.time_ns()}"
                )
                context.abort_requested = False

                context.create_background_task(
                    AudioReceiveProcessor().prompt_bind_device(context, transport),
                    conversation_scoped=False,
                )
            except Exception as e:
                logger.bind(tag=TAG).error(f"播放绑定提示失败: {e}")

    async def _save_memory_async(
        self,
        context: SessionContext,
        session_id: str = None,
        dialogue_snapshot=None,
    ):
        """Persist title and memory before releasing session-owned resources."""
        try:
            session_id = session_id or context.session_id
            dialogue_snapshot = (
                list(dialogue_snapshot)
                if dialogue_snapshot is not None
                else list(context.dialogue.dialogue)
            )
            tasks = []
            if session_id:
                tasks.append(generate_and_save_chat_title(session_id))

            memory_instance = None
            if context.component_manager:
                memory_component = await context.component_manager.get_component(
                    ComponentType.MEMORY, context
                )
                memory_instance = getattr(memory_component, "memory_instance", None)

            if (
                memory_instance
                and context.dialogue
                and hasattr(memory_instance, "save_memory")
            ):
                tasks.append(
                    memory_instance.save_memory(
                        dialogue_snapshot, session_id
                    )
                )

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        logger.bind(tag=TAG).error(f"保存会话数据失败: {result}")

        except Exception as e:
            logger.bind(tag=TAG).error(f"保存会话数据失败: {e}")

    async def _finalize_conversation_session(
        self, context: SessionContext, session_id: str = None
    ):
        session_id = session_id or context.session_id
        if not session_id:
            return

        if session_id != context.session_id:
            if context.last_finalized_session_id != session_id:
                logger.bind(tag=TAG).warning(
                    "忽略非当前会话的结束请求: requested={}, current={}",
                    session_id,
                    context.session_id,
                )
            return

        if not hasattr(context, "_conversation_finalize_lock"):
            context._conversation_finalize_lock = asyncio.Lock()

        async with context._conversation_finalize_lock:
            context.accepting_input_audio = False
            if context.last_finalized_session_id == session_id:
                return
            if not context.conversation_active and not context.dialogue.dialogue:
                return

            # Publish the terminal state before the first await. MQTT control
            # frames can be dispatched while persistence/cleanup is running;
            # delayed start/detect must not revive this logical session.
            context.conversation_active = False
            context.listen_stop_pending = False
            context.abort_requested = True
            await context.cancel_conversation_tasks()
            context.listen_stop_task = None
            context.listen_start_task = None
            context.listen_stop_deadline = 0.0

            if context.component_manager and hasattr(context.component_manager, "get"):
                vad_component = context.component_manager.get(
                    ComponentType.VAD.value
                )
                vad_instance = getattr(vad_component, "vad_instance", None)
                if vad_instance and hasattr(vad_instance, "release_conn_resources"):
                    vad_instance.release_conn_resources(context)

            dialogue_snapshot = list(context.dialogue.dialogue)
            try:
                persistence_timeout = max(
                    0.01,
                    float(
                        context.config.get(
                            "session_persistence_timeout", 5
                        )
                        or 5
                    ),
                )
            except (TypeError, ValueError):
                persistence_timeout = 5.0
            try:
                await asyncio.wait_for(
                    self._save_memory_async(
                        context, session_id, dialogue_snapshot
                    ),
                    timeout=persistence_timeout,
                )
            except asyncio.TimeoutError:
                logger.bind(tag=TAG).warning(
                    "会话持久化超时，继续释放会话资源: session_id={}, timeout={}s",
                    session_id,
                    persistence_timeout,
                )

            tts_component = None
            if context.component_manager:
                tts_component = await context.component_manager.get_component(
                    ComponentType.TTS, context
                )
            tts_instance = getattr(tts_component, "tts_instance", None)
            if tts_instance:
                for queue_name in ("tts_text_queue", "tts_audio_queue"):
                    pending_queue = getattr(tts_instance, queue_name, None)
                    if pending_queue:
                        while True:
                            try:
                                pending_queue.get_nowait()
                            except Exception:
                                break
                tts_instance.tts_audio_first_sentence = True

            keeps_connection = bool(
                getattr(
                    getattr(context, "transport", None),
                    "keeps_connection_between_sessions",
                    False,
                )
            )
            mcp_client = context.mcp_client
            if mcp_client and not keeps_connection:
                mcp_cleanup = getattr(
                    context, "_mcp_cleanup_callback", None
                )
                if mcp_cleanup:
                    context.unregister_cleanup(mcp_cleanup)
                    context._mcp_cleanup_callback = None
                if hasattr(mcp_client, "close"):
                    await mcp_client.close()

            if context.func_handler:
                iot_executor = getattr(
                    context.func_handler, "device_iot_executor", None
                )
                if iot_executor:
                    iot_executor.iot_tools.clear()
                tool_manager = getattr(context.func_handler, "tool_manager", None)
                if tool_manager:
                    tool_manager.refresh_tools()

            context.clear_audio_buffer()
            context.reset_voice_state()
            context.dialogue = Dialogue()
            context.current_speaker = None
            context.introduced_speakers.clear()
            context.system_introduced_speakers.clear()
            context.iot_descriptors.clear()
            context.aec_audio_cache.clear()
            context.aec_audio_cache_time.clear()
            context.audio_flow_control.clear()
            if not keeps_connection:
                context.mcp_client = None
            context.sentence_id = f"ended:{session_id}:{time.time_ns()}"
            if tts_instance:
                tts_instance.current_sentence_id = context.sentence_id
            context.just_woken_up = False
            context.is_speaking = False
            context.close_after_chat = False
            context.llm_finish_task = True
            context.abort_requested = False
            context.accepting_input_audio = False
            context.last_finalized_session_id = session_id
            logger.bind(tag=TAG).info(f"会话资源已结束: {session_id}")

    async def _check_timeout(self, context: SessionContext, transport: TransportInterface):
        """定期检查连接超时"""
        timeout_seconds = context.config.get("close_connection_no_voice_time", 120)
        check_interval = max(1, min(30, timeout_seconds // 4))

        try:
            while transport.is_connected:
                await asyncio.sleep(check_interval)

                timed_out = await self.message_router.timeout_processor.handle_timeout(
                    context,
                    transport,
                )
                if timed_out and not transport.keeps_connection_between_sessions:
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.bind(tag=TAG).error(f"超时检查出错: {e}")
