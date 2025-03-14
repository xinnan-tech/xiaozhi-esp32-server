import os
import json
import uuid
import time
import queue
import asyncio
import traceback
from config.logger import setup_logging
import threading
import websockets
from typing import Dict, Any
from core.utils.dialogue import Message, Dialogue
from core.handle.textHandle import handleTextMessage
from core.utils.util import get_string_no_punctuation_or_emoji, extract_json_from_string
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from core.handle.sendAudioHandle import sendAudioMessage
from core.handle.receiveAudioHandle import handleAudioMessage
from core.handle.intentHandler import Action, get_functions, handle_llm_function_call
from config.private_config import PrivateConfig
from core.auth import AuthMiddleware, AuthenticationError
from core.utils.auth_code_gen import AuthCodeGenerator

TAG = __name__


class TTSException(RuntimeError):
    pass


class ConnectionHandler:
    def __init__(self, config: Dict[str, Any], _vad, _asr, _llm, _tts, _music, _memory, _intent):
        self.config = config
        self.logger = setup_logging()
        self.auth = AuthMiddleware(config)

        self.websocket = None
        self.headers = None
        self.session_id = None
        self.prompt = None
        self.welcome_msg = None

        # 客户端状态相关
        self.client_abort = False
        self.client_listen_mode = "auto"

        # 线程任务相关
        self.loop = asyncio.get_event_loop()
        self.stop_event = threading.Event()
        self.tts_queue = queue.Queue()
        self.audio_play_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=10)

        # 依赖的组件
        self.vad = _vad
        self.asr = _asr
        self.llm = _llm
        self.tts = _tts
        self.memory = _memory
        self.intent = _intent

        # vad相关变量
        self.client_audio_buffer = bytes()
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

        self.cmd_exit = self.config["CMD_exit"]
        self.max_cmd_length = 0
        for cmd in self.cmd_exit:
            if len(cmd) > self.max_cmd_length:
                self.max_cmd_length = len(cmd)

        self.private_config = None
        self.auth_code_gen = AuthCodeGenerator.get_instance()
        self.is_device_verified = False  # 添加设备验证状态标志
        self.music_handler = _music
        self.close_after_chat = False  # 是否在聊天结束后关闭连接
        self.use_function_call_mode = False
        if self.config["selected_module"]["Intent"] == 'function_call':
            self.use_function_call_mode = True

    async def handle_connection(self, ws):
        try:
            # 获取并验证headers
            self.headers = dict(ws.request.headers)
            # 获取客户端ip地址
            client_ip = ws.remote_address[0]
            self.logger.bind(tag=TAG).info(f"{client_ip} conn - Headers: {self.headers}")

            # 进行认证
            await self.auth.authenticate(self.headers)

            device_id = self.headers.get("device-id", None)
            self.memory.init_memory(device_id, self.llm)
            self.intent.set_llm(self.llm)

            # Load private configuration if device_id is provided
            bUsePrivateConfig = self.config.get("use_private_config", False)
            self.logger.bind(tag=TAG).info(f"bUsePrivateConfig: {bUsePrivateConfig}, device_id: {device_id}")
            if bUsePrivateConfig and device_id:
                try:
                    self.private_config = PrivateConfig(device_id, self.config, self.auth_code_gen)
                    await self.private_config.load_or_create()
                    # 判断是否已经绑定
                    owner = self.private_config.get_owner()
                    self.is_device_verified = owner is not None

                    if self.is_device_verified:
                        await self.private_config.update_last_chat_time()

                    llm, tts = self.private_config.create_private_instances()
                    if all([llm, tts]):
                        self.llm = llm
                        self.tts = tts
                        self.logger.bind(tag=TAG).info(f"Loaded private config and instances for device {device_id}")
                    else:
                        self.logger.bind(tag=TAG).error(f"Failed to create instances for device {device_id}")
                        self.private_config = None
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"Error initializing private config: {e}")
                    self.private_config = None
                    raise

            # 认证通过,继续处理
            self.websocket = ws
            self.session_id = str(uuid.uuid4())

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id
            await self.websocket.send(json.dumps(self.welcome_msg))

            await self.loop.run_in_executor(None, self._initialize_components)

            # tts 消化线程
            tts_priority = threading.Thread(target=self._tts_priority_thread, daemon=True)
            tts_priority.start()

            # 音频播放 消化线程
            audio_play_priority = threading.Thread(target=self._audio_play_priority_thread, daemon=True)
            audio_play_priority.start()

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("客户端断开连接")
                await self.close()

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            await ws.close()
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.bind(tag=TAG).error(f"Connection error: {str(e)}-{stack_trace}")
            await ws.close()
            return
        finally:
            await self.memory.save_memory(self.dialogue.dialogue)

    async def _route_message(self, message):
        """消息路由"""
        if isinstance(message, str):
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            await handleAudioMessage(self, message)

    def _initialize_components(self):
        self.prompt = self.config["prompt"]
        if self.private_config:
            self.prompt = self.private_config.private_config.get("prompt", self.prompt)
        # 赋予LLM时间观念
        if "{date_time}" in self.prompt:
            date_time = time.strftime("%Y-%m-%d %H:%M", time.localtime())
            self.prompt = self.prompt.replace("{date_time}", date_time)
        self.dialogue.put(Message(role="system", content=self.prompt))

    async def _check_and_broadcast_auth_code(self):
        """检查设备绑定状态并广播认证码"""
        if not self.private_config.get_owner():
            auth_code = self.private_config.get_auth_code()
            if auth_code:
                # 发送验证码语音提示
                text = f"请在后台输入验证码：{' '.join(auth_code)}"
                self.recode_first_last_text(text)
                future = self.executor.submit(self.speak_and_play, text)
                self.tts_queue.put(future)
            return False
        return True

    def isNeedAuth(self):
        bUsePrivateConfig = self.config.get("use_private_config", False)
        if not bUsePrivateConfig:
            # 如果不使用私有配置，就不需要验证
            return False
        return not self.is_device_verified

    def chat(self, query):
        if self.isNeedAuth():
            self.llm_finish_task = True
            future = asyncio.run_coroutine_threadsafe(self._check_and_broadcast_auth_code(), self.loop)
            future.result()
            return True

        self.dialogue.put(Message(role="user", content=query))

        response_message = []
        processed_chars = 0  # 跟踪已处理的字符位置
        try:
            start_time = time.time()
            # 使用带记忆的对话
            future = asyncio.run_coroutine_threadsafe(self.memory.query_memory(query), self.loop)
            memory_str = future.result()

            self.logger.bind(tag=TAG).debug(f"记忆内容: {memory_str}")
            llm_responses = self.llm.response(
                self.session_id,
                self.dialogue.get_llm_dialogue_with_memory(memory_str)
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        self.llm_finish_task = False
        text_index = 0
        for content in llm_responses:
            response_message.append(content)
            if self.client_abort:
                break

            end_time = time.time()
            self.logger.bind(tag=TAG).debug(f"大模型返回时间: {end_time - start_time} 秒, 生成token={content}")

            # 合并当前全部文本并处理未分割部分
            full_text = "".join(response_message)
            current_text = full_text[processed_chars:]  # 从未处理的位置开始

            # 查找最后一个有效标点
            punctuations = ("。", "？", "！", "；", "：")
            last_punct_pos = -1
            for punct in punctuations:
                pos = current_text.rfind(punct)
                if pos > last_punct_pos:
                    last_punct_pos = pos

            # 找到分割点则处理
            if last_punct_pos != -1:
                segment_text_raw = current_text[:last_punct_pos + 1]
                segment_text = get_string_no_punctuation_or_emoji(segment_text_raw)
                if segment_text:
                    # 强制设置空字符，测试TTS出错返回语音的健壮性
                    # if text_index % 2 == 0:
                    #     segment_text = " "
                    text_index += 1
                    self.recode_first_last_text(segment_text, text_index)
                    future = self.executor.submit(self.speak_and_play, segment_text, text_index)
                    self.tts_queue.put(future)
                    processed_chars += len(segment_text_raw)  # 更新已处理字符位置

        # 处理最后剩余的文本
        full_text = "".join(response_message)
        remaining_text = full_text[processed_chars:]
        if remaining_text:
            segment_text = get_string_no_punctuation_or_emoji(remaining_text)
            if segment_text:
                text_index += 1
                self.recode_first_last_text(segment_text, text_index)
                future = self.executor.submit(self.speak_and_play, segment_text, text_index)
                self.tts_queue.put(future)

        self.llm_finish_task = True
        self.dialogue.put(Message(role="assistant", content="".join(response_message)))
        self.logger.bind(tag=TAG).debug(json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False))
        return True

    def chat_with_function_calling(self, query):
        self.logger.bind(tag=TAG).debug(f"Chat with function calling start: {query}")
        """Chat with function calling for intent detection using streaming"""
        if self.isNeedAuth():
            self.llm_finish_task = True
            future = asyncio.run_coroutine_threadsafe(self._check_and_broadcast_auth_code(), self.loop)
            future.result()
            return True

        self.dialogue.put(Message(role="user", content=query))

        # Define intent functions
        functions = get_functions()

        response_message = []
        processed_chars = 0  # 跟踪已处理的字符位置
   
        try:
            start_time = time.time()

            # 使用带记忆的对话
            future = asyncio.run_coroutine_threadsafe(self.memory.query_memory(query), self.loop)
            memory_str = future.result()

            #self.logger.bind(tag=TAG).info(f"对话记录: {self.dialogue.get_llm_dialogue_with_memory(memory_str)}")

            # 使用支持functions的streaming接口
            llm_responses = self.llm.response_with_functions(
                self.session_id,
                self.dialogue.get_llm_dialogue_with_memory(memory_str),
                functions=functions
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        self.llm_finish_task = False
        text_index = 0

        # 处理流式响应
        tool_call_flag = False
        function_name = None
        function_id = None
        function_arguments = ""
        content_arguments = ""
        for response in llm_responses:
            content, tools_call = response
            if content is not None and len(content)>0:
                if len(response_message)<=0 and content=="```":
                    tool_call_flag = True

            if tools_call is not None:
                tool_call_flag = True
                if tools_call[0].id is not None:
                    function_id = tools_call[0].id
                if tools_call[0].function.name is not None:
                    function_name = tools_call[0].function.name
                if tools_call[0].function.arguments is not None:
                    function_arguments += tools_call[0].function.arguments

            if content is not None and len(content) > 0:
                if tool_call_flag:
                    content_arguments+=content
                else:
                    response_message.append(content)

                    if self.client_abort:
                        break

                    end_time = time.time()
                    self.logger.bind(tag=TAG).debug(f"大模型返回时间: {end_time - start_time} 秒, 生成token={content}")

                    # 处理文本分段和TTS逻辑
                    # 合并当前全部文本并处理未分割部分
                    full_text = "".join(response_message)
                    current_text = full_text[processed_chars:]  # 从未处理的位置开始

                    # 查找最后一个有效标点
                    punctuations = ("。", "？", "！", "；", "：")
                    last_punct_pos = -1
                    for punct in punctuations:
                        pos = current_text.rfind(punct)
                        if pos > last_punct_pos:
                            last_punct_pos = pos

                    # 找到分割点则处理
                    if last_punct_pos != -1:
                        segment_text_raw = current_text[:last_punct_pos + 1]
                        segment_text = get_string_no_punctuation_or_emoji(segment_text_raw)
                        if segment_text:
                            text_index += 1
                            self.recode_first_last_text(segment_text, text_index)
                            future = self.executor.submit(self.speak_and_play, segment_text, text_index)
                            self.tts_queue.put(future)
                            processed_chars += len(segment_text_raw)  # 更新已处理字符位置

        # 处理最后剩余的文本
        full_text = "".join(response_message)
        remaining_text = full_text[processed_chars:]
        if remaining_text:
            segment_text = get_string_no_punctuation_or_emoji(remaining_text)
            if segment_text:
                text_index += 1
                self.recode_first_last_text(segment_text, text_index)
                future = self.executor.submit(self.speak_and_play, segment_text, text_index)
                self.tts_queue.put(future)

        # 存储对话内容
        if len(response_message)>0:
            self.dialogue.put(Message(role="assistant", content="".join(response_message)))

        # 处理function call
        if tool_call_flag:
            if function_id is None:
                a = extract_json_from_string(content_arguments)
                if a is not None:
                    content_arguments_json = json.loads(a)
                    function_name = content_arguments_json["function_name"]
                    function_arguments = json.dumps(content_arguments_json["args"], ensure_ascii=False)
                    function_id = str(uuid.uuid4().hex)
                else:
                    return []
                function_arguments = json.loads(function_arguments)
            self.logger.bind(tag=TAG).info(f"function_name={function_name}, function_id={function_id}, function_arguments={function_arguments}")
            function_call_data = {
                "name": function_name,
                "id": function_id,
                "arguments": function_arguments
            }
            result = handle_llm_function_call(self, function_call_data)
            self._handle_function_result(result, function_call_data, text_index+1)

        self.llm_finish_task = True
        self.logger.bind(tag=TAG).debug(json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False))

        return True

    def _handle_function_result(self, result, function_call_data, text_index):
        if result.action == Action.RESPONSE: # 直接回复前端
            text = result.response
            self.recode_first_last_text(text, text_index)
            future = self.executor.submit(self.speak_and_play, text, text_index)
            self.tts_queue.put(future)
            self.dialogue.put(Message(role="assistant", content=text))
        if result.action == Action.REQLLM: # 调用函数后再请求llm生成回复
            text = result.response
        if result.action == Action.NOTFOUND:
            text = result.response

        

    def _tts_priority_thread(self):
        while not self.stop_event.is_set():
            text = None
            try:
                future = self.tts_queue.get()
                if future is None:
                    continue
                text = None
                opus_datas, text_index, tts_file = [], 0, None
                try:
                    self.logger.bind(tag=TAG).debug("正在处理TTS任务...")
                    tts_timeout = self.config.get("tts_timeout", 10)
                    tts_file, text, text_index = future.result(timeout=tts_timeout)
                    if text is None or len(text) <= 0:
                        self.logger.bind(tag=TAG).error(f"TTS出错：{text_index}: tts text is empty")
                    elif tts_file is None:
                        self.logger.bind(tag=TAG).error(f"TTS出错： file is empty: {text_index}: {text}")
                    else:
                        self.logger.bind(tag=TAG).debug(f"TTS生成：文件路径: {tts_file}")
                        if os.path.exists(tts_file):
                            opus_datas, duration = self.tts.audio_to_opus_data(tts_file)
                        else:
                            self.logger.bind(tag=TAG).error(f"TTS出错：文件不存在{tts_file}")
                except TimeoutError:
                    self.logger.bind(tag=TAG).error("TTS超时")
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"TTS出错: {e}")
                if not self.client_abort:
                    # 如果没有中途打断就发送语音
                    self.audio_play_queue.put((opus_datas, text, text_index))
                if self.tts.delete_audio_file and tts_file is not None and os.path.exists(tts_file):
                    os.remove(tts_file)
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"TTS任务处理错误: {e}")
                self.clearSpeakStatus()
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(json.dumps({"type": "tts", "state": "stop", "session_id": self.session_id})),
                    self.loop
                )
                self.logger.bind(tag=TAG).error(f"tts_priority priority_thread: {text} {e}")

    def _audio_play_priority_thread(self):
        while not self.stop_event.is_set():
            text = None
            try:
                opus_datas, text, text_index = self.audio_play_queue.get()
                future = asyncio.run_coroutine_threadsafe(sendAudioMessage(self, opus_datas, text, text_index),
                                                          self.loop)
                future.result()
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"audio_play_priority priority_thread: {text} {e}")

    def speak_and_play(self, text, text_index=0):
        if text is None or len(text) <= 0:
            self.logger.bind(tag=TAG).info(f"无需tts转换，query为空，{text}")
            return None, text, text_index
        tts_file = self.tts.to_tts(text)
        if tts_file is None:
            self.logger.bind(tag=TAG).error(f"tts转换失败，{text}")
            return None, text, text_index
        self.logger.bind(tag=TAG).debug(f"TTS 文件生成完毕: {tts_file}")
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

    async def close(self):
        """资源清理方法"""

        # 清理其他资源
        self.stop_event.set()
        self.executor.shutdown(wait=False)
        if self.websocket:
            await self.websocket.close()
        self.logger.bind(tag=TAG).info("连接资源已释放")

    def reset_vad_states(self):
        self.client_audio_buffer = bytes()
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
