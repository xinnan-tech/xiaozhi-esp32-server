import os
import json
import uuid
import time
import queue
import asyncio
import logging
import threading
import websockets
from typing import Dict, Any
from collections import deque
from core.utils.util import is_segment
from core.utils.dialogue import Message, Dialogue
from core.handle.textHandle import handleTextMessage
from core.utils.util import get_string_no_punctuation_or_emoji
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from core.handle.audioHandle import handleAudioMessage, sendAudioMessage, sendAudioMessageStream


class ConnectionHandler:
    def __init__(self, config: Dict[str, Any], _vad, _asr, _llm, _tts):
        self.config = config
        self.logger = logging.getLogger(__name__)

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
        self.tts_stream_queue = queue.Queue()
        self.executor = ThreadPoolExecutor(max_workers=self.config["TTS"]["TTS_MAX_WORKERS"])
        self.scheduled_tasks = deque()

        # 依赖的组件
        self.vad = _vad
        self.asr = _asr
        self.llm = _llm
        self.tts = _tts
        self.dialogue = None

        # vad相关变量
        self.client_audio_buffer = bytes()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0.0
        self.client_voice_stop = False

        # asr相关变量
        self.asr_audio = []
        self.asr_server_receive = True

        # llm相关变量
        self.llm_finish_task = False
        self.dialogue = Dialogue()

        # tts相关变量
        self.tts_first_text = None
        self.tts_last_text = None
        self.tts_start_speak_time = None
        self.tts_duration = 0

    async def handle_connection(self, ws):
        self.websocket = ws
        """处理单个WebSocket连接"""
        self.headers = dict(self.websocket.request.headers)
        self.logger.info(f"连接建立，请求头：\n{self.headers}")

        self.welcome_msg = self.config["xiaozhi"]
        self.session_id = str(uuid.uuid4())
        self.welcome_msg["session_id"] = self.session_id
        await self.websocket.send(json.dumps(self.welcome_msg))

        await self.loop.run_in_executor(None, self._initialize_components)

        # tts_priority = threading.Thread(target=self._priority_thread, daemon=True)
        tts_priority = threading.Thread(target=self._priority_thread_stream, daemon=True)
        tts_priority.start()

        try:
            async for message in self.websocket:
                await self._route_message(message)
        except websockets.exceptions.ConnectionClosed:
            self.logger.info("客户端断开连接")
            await self.close()

    async def _route_message(self, message):
        """消息路由"""
        if isinstance(message, str):
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            await handleAudioMessage(self, message)

    def _initialize_components(self):
        self.prompt = self.config["prompt"]
        # 赋予LLM时间观念
        if "{date_time}" in self.prompt:
            date_time = time.strftime("%Y-%m-%d %H:%M", time.localtime())
            self.prompt = self.prompt.replace("{date_time}", date_time)
        self.dialogue.put(Message(role="system", content=self.prompt))

    def chat(self, query):
        self.dialogue.put(Message(role="user", content=query))
        response_message = []
        start = 0
        # 提交 LLM 任务
        try:
            start_time = time.time()  # 记录开始时间
            llm_responses = self.llm.response(self, self.dialogue.get_llm_dialogue())
        except Exception as e:
            self.logger.error(f"LLM 处理出错 {query}: {e}")
            return None
        # 提交 TTS 任务到线程池
        self.llm_finish_task = False
        for content in llm_responses:
            response_message.append(content)
            # 如果中途被打断，就停止生成
            if self.client_abort:
                start = len(response_message)
                break

            end_time = time.time()  # 记录结束时间
            self.logger.debug(f"大模型返回时间时间: {end_time - start_time} 秒, 生成token={content}")
            if is_segment(response_message):
                segment_text = "".join(response_message[start:])
                segment_text = get_string_no_punctuation_or_emoji(segment_text)
                if len(segment_text) > 0:
                    self.recode_first_last_text(segment_text)
                    chunk_queque = queue.Queue()
                    try:
                        self.executor.submit(self.speak_and_play_queue, segment_text,chunk_queque)
                        self.tts_stream_queue.put({
                            "text": segment_text,
                            "chunk_queque": chunk_queque
                        })
                    except Exception as e:
                        self.logger.error(f"TTS 处理出错 {segment_text}: {e}")
                    start = len(response_message)

        # 处理剩余的响应
        if start < len(response_message):
            segment_text = "".join(response_message[start:])
            self.recode_first_last_text(segment_text)
            chunk_queque = queue.Queue()
            self.executor.submit(self.speak_and_play_queue, segment_text,chunk_queque)
            self.tts_stream_queue.put({
                "text": segment_text,
                "chunk_queque": chunk_queque
            })

        self.llm_finish_task = True
        # 更新对话
        self.dialogue.put(Message(role="assistant", content="".join(response_message)))
        self.logger.debug(json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False))
        return True

    def _priority_thread_stream(self):
        while not self.stop_event.is_set():
            text = None
            try:
                tts_stream_queue_msg = self.tts_stream_queue.get()
                try:
                    text = tts_stream_queue_msg["text"]
                    chunk_queque = tts_stream_queue_msg["chunk_queque"]
                except TimeoutError:
                    self.logger.error("TTS 任务超时")
                    continue
                except Exception as e:
                    self.logger.error(f"TTS 任务出错: {e}")
                    continue
                if not self.client_abort:
                    # 如果没有中途打断就发送语音
                    asyncio.run_coroutine_threadsafe(
                        sendAudioMessageStream(self, chunk_queque, 0, text), self.loop
                    )
            except Exception as e:
                self.clearSpeakStatus()
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(json.dumps({"type": "tts", "state": "stop", "session_id": self.session_id})),
                    self.loop
                )
                self.logger.error(f"tts_priority priority_thread: {text}{e}")

    def _priority_thread(self):
        while not self.stop_event.is_set():
            text = None
            try:
                future = self.tts_queue.get()
                text = None
                try:
                    tts_file, text = future.result(timeout=10)
                    if os.path.exists(tts_file):
                        opus_datas, duration = self.tts.wav_to_opus_data(tts_file)
                    else:
                        opus_datas = []
                        duration = 0
                except TimeoutError:
                    self.logger.error("TTS 任务超时")
                    continue
                except Exception as e:
                    self.logger.error(f"TTS 任务出错: {e}")
                    continue
                if not self.client_abort:
                    # 如果没有中途打断就发送语音
                    asyncio.run_coroutine_threadsafe(
                        sendAudioMessage(self, opus_datas, duration, text), self.loop
                    )
                if self.tts.delete_audio_file and os.path.exists(tts_file):
                    os.remove(tts_file)
            except Exception as e:
                self.clearSpeakStatus()
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(json.dumps({"type": "tts", "state": "stop", "session_id": self.session_id})),
                    self.loop
                )
                self.logger.error(f"tts_priority priority_thread: {text}{e}")

    def speak_and_play_queue(self,text,tts_queque):
        if text is None or len(text) <= 0:
            print(f"无需tts转换，query为空，{text}")
            return None
        self.tts.to_tts_stream_queue(text,tts_queque)
        if tts_queque is None:
            print(f"tts转换失败，{text}")

    def speak_and_play(self, text):
        if text is None or len(text) <= 0:
            self.logger.info(f"无需tts转换，query为空，{text}")
            return None
        tts_file = self.tts.to_tts(text)
        if tts_file is None:
            self.logger.error(f"tts转换失败，{text}")
            return None
        self.logger.debug(f"TTS 文件生成完毕")
        return tts_file, text

    def clearSpeakStatus(self):
        self.logger.debug(f"清除服务端讲话状态")
        self.asr_server_receive = True
        self.tts_last_text = None
        self.tts_first_text = None
        self.tts_duration = 0
        self.tts_start_speak_time = None

    def recode_first_last_text(self, text):
        if not self.tts_first_text:
            self.tts_first_text = text
        self.tts_last_text = text

    async def close(self):
        """资源清理方法"""
        self.stop_event.set()
        self.executor.shutdown(wait=False)
        if self.websocket:
            await self.websocket.close()
        self.logger.info("连接资源已释放")

    def reset_vad_states(self):
        self.client_audio_buffer = bytes()
        self.client_have_voice = False
        self.client_have_voice_last_time = 0
        self.client_voice_stop = False
        self.logger.debug("VAD states reset.")

    def stop_all_tasks(self):
        while self.scheduled_tasks:
            task = self.scheduled_tasks.popleft()
            task.cancel()
        self.scheduled_tasks.clear()
