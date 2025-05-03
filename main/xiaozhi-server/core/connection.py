import os
import copy
import json
import uuid
import time
import queue
import asyncio
import traceback

import threading
import websockets
from typing import Dict, Any
from plugins_func.loadplugins import auto_import_modules
from config.logger import setup_logging
from core.utils.dialogue import Message, Dialogue
from core.handle.textHandle import handleTextMessage
from core.utils.util import (
    get_string_no_punctuation_or_emoji,
    extract_json_from_string,
    initialize_modules,
)
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from core.handle.sendAudioHandle import sendAudioMessage
from core.handle.receiveAudioHandle import handleAudioMessage
from core.handle.functionHandler import FunctionHandler
from plugins_func.register import Action, ActionResponse
from core.auth import AuthMiddleware, AuthenticationError
from core.mcp.manager import MCPManager
from config.config_loader import get_private_config_from_api
from config.manage_api_client import DeviceNotFoundException, DeviceBindException
from core.utils.output_counter import add_device_output
from core.handle.ttsReportHandle import enqueue_tts_report, report_tts

TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _tts,
        _memory,
        _intent,
        server=None,
    ):
        self.config = config
        self.server = server
        self.logger = setup_logging()
        self.auth = AuthMiddleware(config)

        self.need_bind = False
        self.bind_code = None
        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.client_ip_info = {}
        self.session_id = None
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0

        # 客户端状态相关
        self.client_abort = False
        self.client_listen_mode = "auto"

        # 线程任务相关
        self.loop = asyncio.get_event_loop()
        self.stop_event = threading.Event()
        self.tts_queue = queue.Queue()
        self.audio_play_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=10)

        # 上报线程
        self.tts_report_queue = queue.Queue()
        self.tts_report_thread = None

        # 依赖的组件
        self.vad = _vad
        self.asr = _asr
        self.llm = _llm
        self.tts = _tts
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_no_voice_last_time = 0.0
        self.client_voice_stop = False

        # asr相关变量
        self.asr_audio = []
        self.asr_server_receive = True

        # llm相关变量
        self.llm_finish_task = False
        self.dialogue = Dialogue()

        # tts相关变量
        self.tts_first_text_index = -1
        self.tts_last_text_index = -1

        # iot相关变量
        self.iot_descriptors = {}
        self.func_handler = None

        self.cmd_exit = self.config["exit_commands"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        self.close_after_chat = False  # 是否在聊天结束后关闭连接
        self.use_function_call_mode = False

        self.timeout_task = None
        self.timeout_seconds = (
            int(self.config.get("close_connection_no_voice_time", 120)) + 60
        )  # 在原来第一道关闭的基础上加60秒，进行二道关闭

    async def handle_connection(self, ws):
        try:
            # 获取并验证headers
            self.headers = dict(ws.request.headers)

            if self.headers.get("device-id", None) is None:
                # 尝试从 URL 的查询参数中获取 device-id
                from urllib.parse import parse_qs, urlparse

                # 从 WebSocket 请求中获取路径
                request_path = ws.request.path
                if not request_path:
                    self.logger.bind(tag=TAG).error("无法获取请求路径")
                    return
                parsed_url = urlparse(request_path)
                query_params = parse_qs(parsed_url.query)
                if "device-id" in query_params:
                    self.headers["device-id"] = query_params["device-id"][0]
                    self.headers["client-id"] = query_params["client-id"][0]
                else:
                    self.logger.bind(tag=TAG).error(
                        "无法从请求头和URL查询参数中获取device-id"
                    )
                    return

            # 获取客户端ip地址
            self.client_ip = ws.remote_address[0]
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            # 进行认证
            await self.auth.authenticate(self.headers)

            # 认证通过,继续处理
            self.websocket = ws
            self.device_id = self.headers.get("device-id", None)
            self.session_id = str(uuid.uuid4())

            # 启动超时检查任务
            self.timeout_task = asyncio.create_task(self._check_timeout())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.websocket.send(json.dumps(self.welcome_msg))

            # 获取差异化配置
            private_config = self._initialize_private_config()
            # 异步初始化
            self.executor.submit(self._initialize_components, private_config)
            # tts 消化线程
            self.tts_priority_thread = threading.Thread(
                target=self._tts_priority_thread, daemon=True
            )
            self.tts_priority_thread.start()

            # 音频播放 消化线程
            self.audio_play_priority_thread = threading.Thread(
                target=self._audio_play_priority_thread, daemon=True
            )
            self.audio_play_priority_thread.start()

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.bind(tag=TAG).error(f"Connection error: {str(e)}-{stack_trace}")
            return
        finally:
            await self._save_and_close(ws)

    async def _save_and_close(self, ws):
        """保存记忆并关闭连接"""
        try:
            await self.memory.save_memory(self.dialogue.dialogue)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"保存记忆失败: {e}")
        finally:
            await self.close(ws)

    async def reset_timeout(self):
        """重置超时计时器"""
        if self.timeout_task:
            self.timeout_task.cancel()
        self.timeout_task = asyncio.create_task(self._check_timeout())

    async def _route_message(self, message):
        """消息路由"""
        # 重置超时计时器
        await self.reset_timeout()

        if isinstance(message, str):
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            await handleAudioMessage(self, message)

    async def handle_config_update(self, message):
        """处理配置更新请求"""
        content = message.get("content", {})
        new_config = content

        # 遍历所有支持的配置模块
        updated_modules = []
        for config_model in ["tts", "llm", "vad", "asr", "memory", "intent"]:
            if config_model not in new_config:
                continue

            new_content = new_config[config_model]
            old_content = self.config.get(config_model, {})

            # 记录配置变更
            self.logger.bind(tag=TAG).info(
                f"配置更新: {config_model} 旧值: {json.dumps(old_content, ensure_ascii=False)} "
                f"新值: {json.dumps(new_content, ensure_ascii=False)}"
            )

            # 深度合并配置
            if isinstance(old_content, dict) and isinstance(new_content, dict):
                merged = {**old_content, **new_content}
                self.config[config_model] = merged
            else:
                self.config[config_model] = new_content

            # 标记需要重新初始化的模块
            if config_model in ["llm", "tts", "asr", "vad", "intent", "memory"]:
                updated_modules.append(config_model)

        # 同步更新 WebSocketServer 的配置
        if self.server:
            async with self.server.config_lock:  # 使用锁确保线程安全
                for config_model in updated_modules:
                    self.server.config[config_model].update(new_config[config_model])

        # 批量初始化模块
        if updated_modules:
            try:
                self._initialize_components(self.config)
                self.logger.bind(tag=TAG).info(
                    f"已重新初始化模块: {', '.join(updated_modules)}"
                )
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"模块初始化失败: {str(e)}")
                await self.websocket.send(
                    json.dumps(
                        {
                            "type": "config_update_response",
                            "status": "error",
                            "message": f"模块初始化失败: {str(e)}",
                        }
                    )
                )
                return

        # 返回成功响应
        await self.websocket.send(
            json.dumps(
                {
                    "type": "config_update_response",
                    "status": "success",
                    "message": f"已更新配置: {', '.join(updated_modules)}",
                }
            )
        )

    def _initialize_components(self, private_config):
        """初始化组件"""
        if private_config is not None:
            self._initialize_models(private_config)
        else:
            self.prompt = self.config["prompt"]
            self.change_system_prompt(self.prompt)
        """加载记忆"""
        self._initialize_memory()
        """加载意图识别"""
        self._initialize_intent()
        """初始化上报线程"""
        self._init_report_threads()

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api:
            return
        if self.tts_report_thread is None or not self.tts_report_thread.is_alive():
            self.tts_report_thread = threading.Thread(
                target=self._tts_report_worker, daemon=True
            )
            self.tts_report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程已启动")

    def _initialize_private_config(self):
        """如果是从配置文件获取，则进行二次实例化"""
        if not self.read_config_from_api:
            return
        """从接口获取差异化的配置进行二次实例化，非全量重新实例化"""
        try:
            begin_time = time.time()
            private_config = get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} 秒，获取差异化配置成功: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"获取差异化配置失败: {e}")
            private_config = {}

        init_tts = False
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]

        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                False,
                False,
                False,
                init_tts,
                False,
                False,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("prompt", None) is not None:
            self.change_system_prompt(modules["prompt"])
            private_config["prompt"] = None
        return private_config

    def _initialize_models(self, private_config):
        init_vad, init_asr, init_llm, init_memory, init_intent = (
            False,
            False,
            False,
            False,
            False,
        )
        if private_config.get("VAD", None) is not None:
            init_vad = True
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if private_config.get("ASR", None) is not None:
            init_asr = True
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            self.config["selected_module"]["Intent"] = private_config[
                "selected_module"
            ]["Intent"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        try:
            modules = initialize_modules(
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                False,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"初始化组件失败: {e}")
            modules = {}
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        """初始化记忆模块"""
        self.memory.init_memory(self.device_id, self.llm)

    def _initialize_intent(self):
        if (
            self.config["Intent"][self.config["selected_module"]["Intent"]]["type"]
            == "function_call"
        ):
            self.use_function_call_mode = True
        """初始化意图识别模块"""
        # 获取意图识别配置
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # 如果使用 nointent，直接返回
        if intent_type == "nointent":
            return
        # 使用 intent_llm 模式
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # 如果配置了专用LLM，则创建独立的LLM实例
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为意图识别创建了专用LLM: {intent_llm_name}, 类型: {intent_llm_type}"
                )
                self.intent.set_llm(intent_llm)
            else:
                # 否则使用主LLM
                self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """加载插件"""
        self.func_handler = FunctionHandler(self)
        self.mcp_manager = MCPManager(self)

        """加载MCP工具"""
        asyncio.run_coroutine_threadsafe(
            self.mcp_manager.initialize_servers(), self.loop
        )
     # 添加对 qwen3 系列模型的支持启用no_think免推理模式
    def change_system_prompt(self, prompt):
        """
        更新系统提示词，并根据模型名称自动添加特定指令 (如 'no_think')。
        """
        final_prompt = prompt
        try:
            # 获取当前选择的LLM模块名称，例如 "OllamaLLM"
            selected_llm_module = self.config.get("selected_module", {}).get("LLM")
            if selected_llm_module:
                # 获取该LLM模块的具体配置
                llm_config = self.config.get("LLM", {}).get(selected_llm_module, {})
                # 获取模型名称
                model_name = llm_config.get("model_name", "")
                
                # 检查模型名称是否以 "qwen3" 开头
                if model_name and isinstance(model_name, str) and model_name.startswith("qwen3"):
                    # 如果是 qwen3 系列模型，在 prompt 前添加 "no_think" 指令
                    final_prompt = f"no_think\\n\\n{prompt}"
                    self.logger.bind(tag=TAG).info(f"检测到模型 {model_name}，已自动添加 'no_think' 指令到系统提示词。")

        except Exception as e:
            # 避免因配置读取错误影响核心功能
            self.logger.bind(tag=TAG).warning(f"检查模型名称以添加 'no_think' 时出错: {e}")

        # 设置最终的 prompt
        self.prompt = final_prompt
        # 更新系统 prompt至对话上下文
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query):

        self.dialogue.put(Message(role="user", content=query))

        response_message = []
        processed_chars = 0  # 跟踪已处理的字符位置
        try:
            # 使用带记忆的对话
            future = asyncio.run_coroutine_threadsafe(
                self.memory.query_memory(query), self.loop
            )
            memory_str = future.result()

            self.logger.bind(tag=TAG).debug(f"记忆内容: {memory_str}")
            llm_responses = self.llm.response(
                self.session_id, self.dialogue.get_llm_dialogue_with_memory(memory_str)
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        self.llm_finish_task = False
        text_index = 0
    # 添加对 qwen3 系列模型的支持启用no_think免推理模式后对think标签的过滤
        # ---- 添加 <think> 过滤状态 ----
        is_thinking = False
        think_buffer = ""
        # -------------------------------

        # 处理流式响应
        for response in llm_responses:
            # ---- <think> 过滤逻辑开始 ----
            raw_chunk = ""
            if isinstance(response, str):
                raw_chunk = response
            else:
                raw_chunk = response.get('content', '')

            if not raw_chunk:
                continue

            think_buffer += raw_chunk
            content_to_process = ""

            while True: # 处理 think_buffer 中的标签
                if is_thinking:
                    end_think_pos = think_buffer.find('</think>')
                    if end_think_pos != -1:
                        think_buffer = think_buffer[end_think_pos + len('</think>'):]
                        is_thinking = False
                        continue # 继续处理剩余 buffer
                    else:
                        think_buffer = "" # 标签未结束，丢弃 buffer
                        break # 等待下一个 chunk
                else: # not is_thinking
                    start_think_pos = think_buffer.find('<think>')
                    if start_think_pos != -1:
                        content_to_process += think_buffer[:start_think_pos] # 添加 <think> 前的内容
                        think_buffer = think_buffer[start_think_pos + len('<think>'):]
                        is_thinking = True
                        continue # 继续处理剩余 buffer
                    else:
                        content_to_process += think_buffer # 没有 <think> 标签，全部添加到待处理内容
                        think_buffer = ""
                        break # 处理完毕，跳出 while

            if not content_to_process:
                continue # 这个 chunk 被完全过滤掉了

            content = content_to_process # 使用过滤后的内容进行后续处理
            # ---- <think> 过滤逻辑结束 ----

            # 原有的逻辑，现在使用过滤后的 content
            if content is not None and len(content) > 0:
                response_message.append(content)

                if self.client_abort:
                    break

        # 处理最后剩余的文本
        full_text = "".join(response_message)
        remaining_text = full_text[processed_chars:]
        if remaining_text:
            segment_text = get_string_no_punctuation_or_emoji(remaining_text)
            if segment_text:
                text_index += 1
                self.recode_first_last_text(segment_text, text_index)
                future = self.executor.submit(
                    self.speak_and_play, segment_text, text_index
                )
                self.tts_queue.put(future)

        self.llm_finish_task = True
        self.dialogue.put(Message(role="assistant", content="".join(response_message)))
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )
        return True

    def chat_with_function_calling(self, query, tool_call=False):
        self.logger.bind(tag=TAG).debug(f"Chat with function calling start: {query}")
        """Chat with function calling for intent detection using streaming"""

        if not tool_call:
            self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = None
        if hasattr(self, "func_handler"):
            functions = self.func_handler.get_functions()
        response_message = []
        processed_chars = 0  # 跟踪已处理的字符位置

        try:
            start_time = time.time()

            # 使用带记忆的对话
            future = asyncio.run_coroutine_threadsafe(
                self.memory.query_memory(query), self.loop
            )
            memory_str = future.result()

            # self.logger.bind(tag=TAG).info(f"对话记录: {self.dialogue.get_llm_dialogue_with_memory(memory_str)}")

            # 使用支持functions的streaming接口
            llm_responses = self.llm.response_with_functions(
                self.session_id,
                self.dialogue.get_llm_dialogue_with_memory(memory_str),
                functions=functions,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        self.llm_finish_task = False
        text_index = 0

        # ---- 添加 <think> 过滤状态 ----
        is_thinking = False
        think_buffer = ""
        # -------------------------------

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""

        for response in llm_responses:
            # ---- <think> 过滤逻辑开始 ----
            # 注意：这里 llm_responses 返回的是 (content, tools_call) 元组
            raw_chunk, tools_call = response
            if raw_chunk is None:
                raw_chunk = ""

            # 处理工具调用信息（如果存在）
            if tools_call is not None:
                tool_call_flag = True # 标记有工具调用
                if tools_call[0].id is not None:
                    function_id = tools_call[0].id
                if tools_call[0].function.name is not None:
                    function_name = tools_call[0].function.name
                if tools_call[0].function.arguments is not None:
                    function_arguments += tools_call[0].function.arguments
                # 工具调用信息不参与 think 标签过滤，直接处理
                # 如果工具调用块也包含 content，需要加入 buffer

            if not raw_chunk:
                 # 即使 raw_chunk 为空，也要检查 tool_call，然后可能跳过
                 if tools_call is None: # 既没有 content 也没有 tool_call
                    continue
                 # 如果只有 tool_call 信息，则处理完后跳过 think 过滤
                 # 但通常 tool_call 会伴随一些 content 或在 content 结束后出现
                 # 谨慎起见，如果 raw_chunk 为空但有 tools_call，我们先不跳过，让 buffer 处理逻辑运行一次
                 pass # 让下面的 buffer 逻辑处理空字符串，确保状态正确

            think_buffer += raw_chunk
            content_to_process = ""

            while True: # 处理 think_buffer 中的标签
                if is_thinking:
                    end_think_pos = think_buffer.find('</think>')
                    if end_think_pos != -1:
                        think_buffer = think_buffer[end_think_pos + len('</think>'):]
                        is_thinking = False
                        continue # 继续处理剩余 buffer
                    else:
                        think_buffer = "" # 标签未结束，丢弃 buffer
                        break # 等待下一个 chunk
                else: # not is_thinking
                    start_think_pos = think_buffer.find('<think>')
                    if start_think_pos != -1:
                        content_to_process += think_buffer[:start_think_pos] # 添加 <think> 前的内容
                        think_buffer = think_buffer[start_think_pos + len('<think>'):]
                        is_thinking = True
                        continue # 继续处理剩余 buffer
                    else:
                        content_to_process += think_buffer # 没有 <think> 标签，全部添加到待处理内容
                        think_buffer = ""
                        break # 处理完毕，跳出 while

            if not content_to_process:
                # 即使 content 被过滤掉，也要检查是否有工具调用要处理
                # (工具调用处理逻辑已在上面完成)
                if tools_call is None: # 既没有可处理内容，也没有工具调用信息
                    continue
                # 如果有工具调用，即使 content 为空，也需要继续后面的逻辑（如果后面有处理工具调用的逻辑）
                # 但在此循环中，我们只关心文本内容的处理
                pass # content 为空，但可能有 tools_call 信息需要后续处理

            content = content_to_process # 使用过滤后的内容进行后续处理
            # ---- <think> 过滤逻辑结束 ----

            # 累加过滤后的文本内容，用于后续可能的非工具调用文本处理或日志记录
            if content is not None and len(content) > 0:
                 content_arguments += content # 累加过滤后的文本，用于判断是否以 <tool_call> 开头等

            # 检查累加的文本是否以 <tool_call> 开头 (这部分逻辑可能需要调整，因为它依赖原始流)
            # 暂时保留，但注意 content_arguments 现在是过滤后的文本
            if not tool_call_flag and content_arguments.startswith("<tool_call>"):
                # print("content_arguments", content_arguments)
                tool_call_flag = True

            # 原有的处理逻辑，现在使用过滤后的 content
            # 只有在非工具调用模式下，才将内容加入 response_message 并进行分段 TTS
            if content is not None and len(content) > 0:
                if not tool_call_flag: # 确保不是工具调用过程中的文本块
                    response_message.append(content)

                    if self.client_abort:
                        break

        # 处理function call
        if tool_call_flag:
            bHasError = False
            if function_id is None:
                a = extract_json_from_string(content_arguments)
                if a is not None:
                    try:
                        content_arguments_json = json.loads(a)
                        function_name = content_arguments_json["name"]
                        function_arguments = json.dumps(
                            content_arguments_json["arguments"], ensure_ascii=False
                        )
                        function_id = str(uuid.uuid4().hex)
                    except Exception as e:
                        bHasError = True
                        response_message.append(a)
                else:
                    bHasError = True
                    response_message.append(content_arguments)
                if bHasError:
                    self.logger.bind(tag=TAG).error(
                        f"function call error: {content_arguments}"
                    )
            if not bHasError:
                response_message.clear()
                self.logger.bind(tag=TAG).debug(
                    f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}"
                )
                function_call_data = {
                    "name": function_name,
                    "id": function_id,
                    "arguments": function_arguments,
                }

                # 处理MCP工具调用
                if self.mcp_manager.is_mcp_tool(function_name):
                    result = self._handle_mcp_tool_call(function_call_data)
                else:
                    # 处理系统函数
                    result = self.func_handler.handle_llm_function_call(
                        self, function_call_data
                    )
                self._handle_function_result(result, function_call_data, text_index + 1)

        # 处理最后剩余的文本
        full_text = "".join(response_message)
        remaining_text = full_text[processed_chars:]
        if remaining_text:
            segment_text = get_string_no_punctuation_or_emoji(remaining_text)
            if segment_text:
                text_index += 1
                self.recode_first_last_text(segment_text, text_index)
                future = self.executor.submit(
                    self.speak_and_play, segment_text, text_index
                )
                self.tts_queue.put(future)

        # 存储对话内容
        if len(response_message) > 0:
            self.dialogue.put(
                Message(role="assistant", content="".join(response_message))
            )

        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(
            json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False)
        )

        return True

    def _handle_mcp_tool_call(self, function_call_data):
        function_arguments = function_call_data["arguments"]
        function_name = function_call_data["name"]
        try:
            args_dict = function_arguments
            if isinstance(function_arguments, str):
                try:
                    args_dict = json.loads(function_arguments)
                except json.JSONDecodeError:
                    self.logger.bind(tag=TAG).error(
                        f"无法解析 function_arguments: {function_arguments}"
                    )
                    return ActionResponse(
                        action=Action.REQLLM, result="参数解析失败", response=""
                    )

            tool_result = asyncio.run_coroutine_threadsafe(
                self.mcp_manager.execute_tool(function_name, args_dict), self.loop
            ).result()
            # meta=None content=[TextContent(type='text', text='北京当前天气:\n温度: 21°C\n天气: 晴\n湿度: 6%\n风向: 西北 风\n风力等级: 5级', annotations=None)] isError=False
            content_text = ""
            if tool_result is not None and tool_result.content is not None:
                for content in tool_result.content:
                    content_type = content.type
                    if content_type == "text":
                        content_text = content.text
                    elif content_type == "image":
                        pass

            if len(content_text) > 0:
                return ActionResponse(
                    action=Action.REQLLM, result=content_text, response=""
                )

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP工具调用错误: {e}")
            return ActionResponse(
                action=Action.REQLLM, result="工具调用出错", response=""
            )

        return ActionResponse(action=Action.REQLLM, result="工具调用出错", response="")

    def _handle_function_result(self, result, function_call_data, text_index):
        if result.action == Action.RESPONSE:  # 直接回复前端
            text = result.response
            self.recode_first_last_text(text, text_index)
            future = self.executor.submit(self.speak_and_play, text, text_index)
            self.tts_queue.put(future)
            self.dialogue.put(Message(role="assistant", content=text))
        elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
            text = result.result
            if text is not None and len(text) > 0:
                function_id = function_call_data["id"]
                function_name = function_call_data["name"]
                function_arguments = function_call_data["arguments"]
                self.dialogue.put(
                    Message(
                        role="assistant",
                        tool_calls=[
                            {
                                "id": function_id,
                                "function": {
                                    "arguments": function_arguments,
                                    "name": function_name,
                                },
                                "type": "function",
                                "index": 0,
                            }
                        ],
                    )
                )

                self.dialogue.put(
                    Message(role="tool", tool_call_id=function_id, content=text)
                )
                self.chat_with_function_calling(text, tool_call=True)
        elif result.action == Action.NOTFOUND or result.action == Action.ERROR:
            text = result.result
            self.recode_first_last_text(text, text_index)
            future = self.executor.submit(self.speak_and_play, text, text_index)
            self.tts_queue.put(future)
            self.dialogue.put(Message(role="assistant", content=text))
        else:
            pass

    def _tts_priority_thread(self):
        while not self.stop_event.is_set():
            text = None
            try:
                try:
                    future = self.tts_queue.get(timeout=1)
                except queue.Empty:
                    if self.stop_event.is_set():
                        break
                    continue
                if future is None:
                    continue
                text = None
                opus_datas, text_index, tts_file = [], 0, None
                try:
                    self.logger.bind(tag=TAG).debug("正在处理TTS任务...")
                    tts_timeout = int(self.config.get("tts_timeout", 10))
                    tts_file, text, text_index = future.result(timeout=tts_timeout)
                    if text is None or len(text) <= 0:
                        self.logger.bind(tag=TAG).error(
                            f"TTS出错：{text_index}: tts text is empty"
                        )
                    elif tts_file is None:
                        self.logger.bind(tag=TAG).error(
                            f"TTS出错： file is empty: {text_index}: {text}"
                        )
                    else:
                        self.logger.bind(tag=TAG).debug(
                            f"TTS生成：文件路径: {tts_file}"
                        )
                        if os.path.exists(tts_file):
                            opus_datas, _ = self.tts.audio_to_opus_data(tts_file)
                            # 在这里上报TTS数据（使用文件路径）
                            enqueue_tts_report(self, 2, text, opus_datas)
                        else:
                            self.logger.bind(tag=TAG).error(
                                f"TTS出错：文件不存在{tts_file}"
                            )
                except TimeoutError:
                    self.logger.bind(tag=TAG).error("TTS超时")
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"TTS出错: {e}")
                if not self.client_abort:
                    # 如果没有中途打断就发送语音
                    self.audio_play_queue.put((opus_datas, text, text_index))
                if (
                    self.tts.delete_audio_file
                    and tts_file is not None
                    and os.path.exists(tts_file)
                ):
                    os.remove(tts_file)
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"TTS任务处理错误: {e}")
                self.clearSpeakStatus()
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(
                        json.dumps(
                            {
                                "type": "tts",
                                "state": "stop",
                                "session_id": self.session_id,
                            }
                        )
                    ),
                    self.loop,
                )
                self.logger.bind(tag=TAG).error(
                    f"tts_priority priority_thread: {text} {e}"
                )

    def _audio_play_priority_thread(self):
        while not self.stop_event.is_set():
            text = None
            try:
                try:
                    opus_datas, text, text_index = self.audio_play_queue.get(timeout=1)
                except queue.Empty:
                    if self.stop_event.is_set():
                        break
                    continue
                future = asyncio.run_coroutine_threadsafe(
                    sendAudioMessage(self, opus_datas, text, text_index), self.loop
                )
                future.result()
            except Exception as e:
                self.logger.bind(tag=TAG).error(
                    f"audio_play_priority priority_thread: {text} {e}"
                )

    def _tts_report_worker(self):
        """TTS上报工作线程"""

        while not self.stop_event.is_set():
            try:
                # 从队列获取数据，设置超时以便定期检查停止事件
                item = self.tts_report_queue.get(timeout=1)
                if item is None:  # 检测毒丸对象
                    break

                type, text, audio_data = item

                try:
                    # 执行上报（传入二进制数据）
                    report_tts(self, type, text, audio_data)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"TTS上报线程异常: {e}")
                finally:
                    # 标记任务完成
                    self.tts_report_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"TTS上报工作线程异常: {e}")

        self.logger.bind(tag=TAG).info("TTS上报线程已退出")

    def speak_and_play(self, text, text_index=0):
        if text is None or len(text) <= 0:
            self.logger.bind(tag=TAG).info(f"无需tts转换，query为空，{text}")
            return None, text, text_index
        tts_file = self.tts.to_tts(text)
        if tts_file is None:
            self.logger.bind(tag=TAG).error(f"tts转换失败，{text}")
            return None, text, text_index
        self.logger.bind(tag=TAG).debug(f"TTS 文件生成完毕: {tts_file}")
        if self.max_output_size > 0:
            add_device_output(self.headers.get("device-id"), len(text))
        return tts_file, text, text_index

    def clearSpeakStatus(self):
        self.logger.bind(tag=TAG).debug(f"清除服务端讲话状态")
        self.asr_server_receive = True
        self.tts_last_text_index = -1
        self.tts_first_text_index = -1

    def recode_first_last_text(self, text, text_index=0):
        if self.tts_first_text_index == -1:
            self.logger.bind(tag=TAG).info(f"大模型说出第一句话: {text}")
            self.tts_first_text_index = text_index
        self.tts_last_text_index = text_index

    async def close(self, ws=None):
        """资源清理方法"""
        # 取消超时任务
        if self.timeout_task:
            self.timeout_task.cancel()
            self.timeout_task = None

        # 清理MCP资源
        if hasattr(self, "mcp_manager") and self.mcp_manager:
            await self.mcp_manager.cleanup_all()

        # 触发停止事件并清理资源
        if self.stop_event:
            self.stop_event.set()

        # 立即关闭线程池
        if self.executor:
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.executor = None

        # 添加毒丸对象到上报队列确保线程退出
        self.tts_report_queue.put(None)

        # 清空任务队列
        self.clear_queues()

        if ws:
            await ws.close()
        elif self.websocket:
            await self.websocket.close()
        self.logger.bind(tag=TAG).info("连接资源已释放")

    def clear_queues(self):
        # 清空所有任务队列
        self.logger.bind(tag=TAG).debug(
            f"开始清理: TTS队列大小={self.tts_queue.qsize()}, 音频队列大小={self.audio_play_queue.qsize()}"
        )
        for q in [self.tts_queue, self.audio_play_queue]:
            if not q:
                continue
            while not q.empty():
                try:
                    q.get_nowait()
                except queue.Empty:
                    continue
            q.queue.clear()
            # 添加毒丸信号到队列，确保线程退出
            # q.queue.put(None)
        self.logger.bind(tag=TAG).debug(
            f"清理结束: TTS队列大小={self.tts_queue.qsize()}, 音频队列大小={self.audio_play_queue.qsize()}"
        )

    def reset_vad_states(self):
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.logger.bind(tag=TAG).debug("VAD states reset.")

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Use the existing chat method
            self.chat(text)

            # After chat is complete, close the connection
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """检查连接超时"""
        try:
            while not self.stop_event.is_set():
                await asyncio.sleep(self.timeout_seconds)
                if not self.stop_event.is_set():
                    self.logger.bind(tag=TAG).info("连接超时，准备关闭")
                    await self.close(self.websocket)
                    break
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"超时检查任务出错: {e}")


def filter_sensitive_info(config: dict) -> dict:
    """
    过滤配置中的敏感信息
    Args:
        config: 原始配置字典
    Returns:
        过滤后的配置字典
    """
    sensitive_keys = [
        "api_key",
        "personal_access_token",
        "access_token",
        "token",
        "access_key_secret",
        "secret_key",
    ]

    def _filter_dict(d: dict) -> dict:
        filtered = {}
        for k, v in d.items():
            if any(sensitive in k.lower() for sensitive in sensitive_keys):
                filtered[k] = "***"
            elif isinstance(v, dict):
                filtered[k] = _filter_dict(v)
            elif isinstance(v, list):
                filtered[k] = [_filter_dict(i) if isinstance(i, dict) else i for i in v]
            else:
                filtered[k] = v
        return filtered

    return _filter_dict(copy.deepcopy(config))
