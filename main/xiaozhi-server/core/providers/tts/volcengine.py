import asyncio
import base64
import json
import uuid
import queue
import websockets

from core.utils import opus_encoder_utils
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from core.utils.tts import MarkdownCleaner
from config.logger import setup_logging
from core.handle.abortHandle import handleAbortMessage
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.DUAL_STREAM
        self.api_key = config.get("api_key")
        self.model_name = config.get("model_name")
        self.host = config.get("host")
        if self.host is None:
            self.host = "ai-gateway.vei.volces.com"
        self.delete_audio_file = delete_audio_file
        self.ws_url = f"wss://{self.host}/v1/realtime?model={self.model_name}"

        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = config.get("voice", "alloy")
        self.audio_file_type = config.get("format", "pcm") # 流式接口通常使用 pcm
        self.sample_rate = config.get("sample_rate", 16000)
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=16000, channels=1, frame_size_ms=60
        )
        # 处理空字符串的情况
        speed = config.get("speed", "1.0")
        self.speed = float(speed) if speed else 1.0
        self.ws = None
        self._monitor_task = None
        check_model_key("TTS", self.api_key)

    

    async def open_audio_channels(self, conn):
        try:
            await super().open_audio_channels(conn)
            await self._ensure_connection()
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to open audio channels: {str(e)}")
            self.ws = None
            raise

    
    async def _receive_audio(self):
        """监听TTS响应"""
        opus_datas_cache = []
        is_first_sentence = True
        is_audio_done = False
        first_sentence_segment_count = 0  # 添加计数器
        try:
            while not self.conn.stop_event.is_set():
                message = await self.ws.recv()
                data = json.loads(message)
                event_type = data.get("type")
                logger.bind(tag=TAG).debug(f"Received data: {data}")
                if event_type == "tts_session.updated":
                    logger.bind(tag=TAG).info(f"TTS session updated: {data}")
                    opus_datas_cache = []
                    is_first_sentence = True
                    first_sentence_segment_count = 0  
                elif event_type == "response.audio.delta":
                    pcm_data = base64.b64decode(data.get("delta"))
                    opus_data_list = self.opus_encoder.encode_pcm_to_opus(pcm_data, False)
                    if len(opus_data_list) == 0:
                        continue
                    if is_first_sentence:
                        logger.bind(tag=TAG).info(f"Received first audio data")
                        is_first_sentence = False
                        self.tts_audio_queue.put(
                            (SentenceType.FIRST, opus_data_list, None)
                        )
                    else:                     
                        logger.bind(tag=TAG).debug(f"Received delta audio data")
                        self.tts_audio_queue.put(
                            (SentenceType.MIDDLE, opus_data_list, None)
                        )
                    first_sentence_segment_count += 1
                elif event_type == "response.audio_subtitle.delta":
                    logger.bind(tag=TAG).info(f"Received subtitles delata data: {data}")
                    subtitles = data.get("subtitles").get("text")
                    if subtitles:
                        self.tts_audio_queue.put(
                            (SentenceType.MIDDLE, [], subtitles)
                        )
                elif event_type == "response.audio.done":
                    logger.bind(tag=TAG).info("完成语音生成.")
                    if self.tts_audio_queue:
                        self.tts_audio_queue.put(
                            (SentenceType.LAST, opus_datas_cache, None)
                        )
                    self._process_before_stop_play_files()
                    break # End of stream for this request
                elif event_type == "error":
                    logger.bind(tag=TAG).error(f"Received error from server: {data}")
                    if self.ws:
                        try:
                            await self.ws.close()
                        except:
                            pass
                    self.ws = None
                    break
        except websockets.exceptions.ConnectionClosed as e:
            logger.bind(tag=TAG).warning(f"WebSocket connection closed: {e}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error receiving audio: {e}")
        finally:
            logger.bind(tag=TAG).info(f"退出音频接收任务")
        
    def tts_text_priority_thread(self):
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                logger.bind(tag=TAG).debug(
                    f"收到TTS任务｜{message.sentence_type.name} ｜ {message.content_type.name} | 会话ID: {self.conn.sentence_id}"
                )
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("收到打断信息，终止TTS文本处理线程")
                    continue
                if message.sentence_type == SentenceType.FIRST:
                    if not getattr(self.conn, "sentence_id", None): 
                            self.conn.sentence_id = uuid.uuid4().hex
                            logger.bind(tag=TAG).info(f"自动生成新的 会话ID: {self.conn.sentence_id}")
                    logger.bind(tag=TAG).debug("开始启动TTS会话...")
                    future = asyncio.run_coroutine_threadsafe(
                        self.start_session(self.conn.sentence_id),
                        loop=self.conn.loop,
                    )
                    future.result()
                    self.tts_stop_request = False
                    self.processed_chars = 0
                    self.tts_text_buff = []
                    self.is_first_sentence = True
                    self.tts_audio_first_sentence = True
                    self.before_stop_play_files.clear()
                    logger.bind(tag=TAG).debug("TTS会话启动成功")
                elif ContentType.TEXT == message.content_type:
                    self.tts_text_buff.append(message.content_detail)
                    segment_text = self._get_segment_text()
                    if segment_text:
                        logger.bind(tag=TAG).info(
                            f"开始发送TTS文本: {message.content_detail}"
                        )
                        future = asyncio.run_coroutine_threadsafe(
                            self.text_to_speak(segment_text, None),
                            loop=self.conn.loop,
                        )
                        future.result()
                elif ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(
                        f"添加音频文件到待播放列表: {message.content_file}"
                    )
                    self.before_stop_play_files.append(
                        (message.content_file, message.content_detail)
                    )

                if message.sentence_type == SentenceType.LAST:
                    logger.bind(tag=TAG).info("结束TTS会话")
                    future = asyncio.run_coroutine_threadsafe(
                        self.finish_session(self.conn.sentence_id),
                        loop=self.conn.loop,
                    )
                    future.result()
            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理TTS文本失败: {str(e)}, 类型: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )
                continue
    
    async def start_session(self, session_id):
        logger.bind(tag=TAG).info(f"开始会话 {session_id}")
        try:
            # 建立新连接
            await self._ensure_connection()
            # 发送会话启动请求
            session_update_payload = {
                "event_id": str(uuid.uuid4()),
                "type": "tts_session.update",
                "session": {
                    "voice": self.voice,
                    "output_audio_format": self.audio_file_type,
                    "output_audio_sample_rate": self.sample_rate,
                    "text_to_speech": {
                        "model": self.model_name
                    }
                }
            }
            await self.ws.send(json.dumps(session_update_payload))
            logger.bind(tag=TAG).info(f"会话启动请求已发送, Send Event: {session_update_payload}")
            # 启动监听任务
            if self._monitor_task is None:
                self._monitor_task = asyncio.create_task(self._receive_audio())
        except Exception as e:
            logger.bind(tag=TAG).error(f"启动会话失败: {str(e)}")
            # 确保清理资源
            if hasattr(self, "_monitor_task"):
                try:
                    self._monitor_task.cancel()
                    await self._monitor_task
                except:
                    pass
                self._monitor_task = None
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
            raise

    async def finish_session(self, session_id):    
        try:
            if self.ws:
                done_payload = {
                "type": "input_text.done"
            }
            await self.ws.send(json.dumps(done_payload))
            logger.bind(tag=TAG).info(f"会话结束请求已发送,Send Event: {done_payload}")

        except Exception as e:
            logger.bind(tag=TAG).error(f"关闭会话失败: {str(e)}")
        
        # 等待监听任务完成
        if hasattr(self, "_monitor_task"):
            try:
                await self._monitor_task
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"等待监听任务完成时发生错误: {str(e)}"
                )
            finally:
                self._monitor_task = None
         
    async def _ensure_connection(self):
        if self.ws is None:
            try:
                logger.bind(tag=TAG).info(f"Connecting to {self.ws_url}")
                headers = {"Authorization": f"Bearer {self.api_key}"}
                self.ws = await websockets.connect(self.ws_url, additional_headers=headers)
                logger.bind(tag=TAG).info("WebSocket connection established.")
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to connect to WebSocket: {e}")
                self.ws = None
                raise
                    
    async def stop_ws_connection(self):      
        # 关闭WebSocket连接
        if self.ws:
            try:
                await self.ws.close()
                logger.bind(tag=TAG).info("WebSocket connection closed.")
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error closing WebSocket: {e}")
            finally:
                self.ws = None
 
    async def text_to_speak(self, text, output_file):
        """发送文本到TTS服务"""
        try:
            # 建立新连接
            if self.ws is None:
                await handleAbortMessage(self.conn)
                logger.bind(tag=TAG).error(f"WebSocket连接不存在，终止发送文本")
                return

            #  过滤Markdown
            filtered_text = MarkdownCleaner.clean_markdown(text)

            # 发送文本
            if len(filtered_text) > 0:
                text_append_payload = {
                    "event_id": str(uuid.uuid4()),
                    "type": "input_text.append",
                    "delta": filtered_text
                }
            await self.ws.send(json.dumps(text_append_payload))
            logger.bind(tag=TAG).info(f"发送文本， Send Event: {text_append_payload}")
            return
        except Exception as e:
            logger.bind(tag=TAG).error(f"发送TTS文本失败: {str(e)}")
            await self.stop_ws_connection()
            raise
                     
            

            