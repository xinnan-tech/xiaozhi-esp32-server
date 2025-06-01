import os
import uuid
import json
import queue
import asyncio
import threading
import traceback
import websockets
import time
from config.logger import setup_logging
from core.utils import opus_encoder_utils
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType

TAG = __name__
logger = setup_logging()

PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

# Message Type:
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_RESPONSE = 0b1011
FULL_SERVER_RESPONSE = 0b1001
ERROR_INFORMATION = 0b1111

# Message Type Specific Flags
MsgTypeFlagNoSeq = 0b0000  # Non-terminal packet with no sequence
MsgTypeFlagPositiveSeq = 0b1  # Non-terminal packet with sequence > 0
MsgTypeFlagLastNoSeq = 0b10  # last packet with no sequence
MsgTypeFlagNegativeSeq = 0b11  # Payload contains event number (int32)
MsgTypeFlagWithEvent = 0b100
# Message Serialization
NO_SERIALIZATION = 0b0000
JSON = 0b0001
# Message Compression
COMPRESSION_NO = 0b0000
COMPRESSION_GZIP = 0b0001

EVENT_NONE = 0
EVENT_Start_Connection = 1

EVENT_FinishConnection = 2

EVENT_ConnectionStarted = 50  # 成功建连

EVENT_ConnectionFailed = 51  # 建连失败（可能是无法通过权限认证）

EVENT_ConnectionFinished = 52  # 连接结束

# 上行Session事件
EVENT_StartSession = 100

EVENT_FinishSession = 102
# 下行Session事件
EVENT_SessionStarted = 150
EVENT_SessionFinished = 152

EVENT_SessionFailed = 153

# 上行通用事件
EVENT_TaskRequest = 200

# 下行TTS事件
EVENT_TTSSentenceStart = 350

EVENT_TTSSentenceEnd = 351

EVENT_TTSResponse = 352


class Header:
    def __init__(
        self,
        protocol_version=PROTOCOL_VERSION,
        header_size=DEFAULT_HEADER_SIZE,
        message_type: int = 0,
        message_type_specific_flags: int = 0,
        serial_method: int = NO_SERIALIZATION,
        compression_type: int = COMPRESSION_NO,
        reserved_data=0,
    ):
        self.header_size = header_size
        self.protocol_version = protocol_version
        self.message_type = message_type
        self.message_type_specific_flags = message_type_specific_flags
        self.serial_method = serial_method
        self.compression_type = compression_type
        self.reserved_data = reserved_data

    def as_bytes(self) -> bytes:
        return bytes(
            [
                (self.protocol_version << 4) | self.header_size,
                (self.message_type << 4) | self.message_type_specific_flags,
                (self.serial_method << 4) | self.compression_type,
                self.reserved_data,
            ]
        )


class Optional:
    def __init__(
        self, event: int = EVENT_NONE, sessionId: str = None, sequence: int = None
    ):
        self.event = event
        self.sessionId = sessionId
        self.errorCode: int = 0
        self.connectionId: str | None = None
        self.response_meta_json: str | None = None
        self.sequence = sequence

    # 转成 byte 序列
    def as_bytes(self) -> bytes:
        option_bytes = bytearray()
        if self.event != EVENT_NONE:
            option_bytes.extend(self.event.to_bytes(4, "big", signed=True))
        if self.sessionId is not None:
            session_id_bytes = str.encode(self.sessionId)
            size = len(session_id_bytes).to_bytes(4, "big", signed=True)
            option_bytes.extend(size)
            option_bytes.extend(session_id_bytes)
        if self.sequence is not None:
            option_bytes.extend(self.sequence.to_bytes(4, "big", signed=True))
        return option_bytes


class Response:
    def __init__(self, header: Header, optional: Optional):
        self.optional = optional
        self.header = header
        self.payload: bytes | None = None

    def __str__(self):
        return super().__str__()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.ws = None  # 初始化ws属性
        self.interface_type = InterfaceType.DUAL_STREAM
        self.appId = config.get("appid")
        self.access_token = config.get("access_token")
        self.cluster = config.get("cluster")
        self.resource_id = config.get("resource_id")
        if config.get("private_voice"):
            self.speaker = config.get("private_voice")
        else:
            self.speaker = config.get("speaker")
        self.voice = config.get("voice")
        self.ws_url = config.get("ws_url")
        self.authorization = config.get("authorization")
        self.header = {"Authorization": f"{self.authorization}{self.access_token}"}
        self.enable_two_way = True
        self.start_connection_flag = False
        self.tts_text = ""
        # 合成文字语音后，播放的音频文件列表
        self.before_stop_play_files = []
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=16000, channels=1, frame_size_ms=60
        )
        check_model_key("TTS", self.access_token)

        # 添加会话状态控制
        self._session_lock = asyncio.Lock()  # 会话操作的并发锁
        self._current_session_id = None  # 当前会话ID
        self._session_started = False  # 会话是否已开始
        self._session_finished = False  # 会话是否已结束
        self._connection_ready = False  # 连接是否就绪
        self._reconnect_attempts = 0  # 重连尝试次数
        self._max_reconnect_attempts = 3  # 最大重连次数

    ###################################################################################
    # 火山双流式TTS重写父类的方法--开始
    ###################################################################################

    async def open_audio_channels(self, conn):
        try:
            await super().open_audio_channels(conn)
            await self._ensure_connection()
            tts_priority = threading.Thread(
                target=self._start_monitor_tts_response_thread, daemon=True
            )
            tts_priority.start()
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to open audio channels: {str(e)}")
            self.ws = None
            raise

    async def _ensure_connection(self):
        """确保WebSocket连接可用"""
        try:
            if self.ws is None:
                logger.bind(tag=TAG).info("WebSocket连接不存在，开始建立新连接...")
                ws_header = {
                    "X-Api-App-Key": self.appId,
                    "X-Api-Access-Key": self.access_token,
                    "X-Api-Resource-Id": self.resource_id,
                    "X-Api-Connect-Id": uuid.uuid4(),
                }
                self.ws = await websockets.connect(
                    self.ws_url, additional_headers=ws_header, max_size=1000000000
                )
                self._connection_ready = True
                self._reconnect_attempts = 0
                logger.bind(tag=TAG).info("WebSocket连接建立成功")
            else:
                # 尝试发送ping来检查连接是否还活着
                try:
                    logger.bind(tag=TAG).debug("检查WebSocket连接状态...")
                    pong_waiter = await self.ws.ping()
                    await asyncio.wait_for(pong_waiter, timeout=1.0)
                    logger.bind(tag=TAG).debug("WebSocket连接状态正常")
                except (asyncio.TimeoutError, websockets.ConnectionClosed):
                    # 如果ping失败，重新建立连接
                    logger.bind(tag=TAG).warning("WebSocket连接已断开，准备重新连接...")
                    try:
                        await self.ws.close()
                    except:
                        pass
                    self.ws = None
                    self._connection_ready = False
                    # 重新建立连接
                    await self._ensure_connection()
        except Exception as e:
            logger.bind(tag=TAG).error(f"确保连接失败: {str(e)}")
            self._connection_ready = False
            self.ws = None
            raise

    def tts_text_priority_thread(self):
        logger.bind(tag=TAG).info("TTS文本处理线程启动")
        while not self.conn.stop_event.is_set():
            try:
                logger.bind(tag=TAG).debug("等待TTS文本队列消息...")
                message = self.tts_text_queue.get(timeout=1)
                logger.bind(tag=TAG).info(
                    f"收到TTS任务｜{message.sentence_type.name} ｜ {message.content_type.name} | 会话ID: {self.conn.sentence_id}"
                )
                if message.sentence_type == SentenceType.FIRST:
                    # 初始化参数
                    try:
                        logger.bind(tag=TAG).info("开始启动TTS会话...")
                        future = asyncio.run_coroutine_threadsafe(
                            self.start_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                        future.result()
                        self.tts_audio_first_sentence = True
                        self.before_stop_play_files.clear()
                        logger.bind(tag=TAG).info("TTS会话启动成功")
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"启动TTS会话失败: {str(e)}")
                        # 直接跳过当前消息，不重新入队
                        time.sleep(1)
                        continue
                elif ContentType.TEXT == message.content_type:
                    if message.content_detail:
                        try:
                            logger.bind(tag=TAG).info(
                                f"开始发送TTS文本: {message.content_detail}"
                            )
                            future = asyncio.run_coroutine_threadsafe(
                                self.text_to_speak(message.content_detail, None),
                                loop=self.conn.loop,
                            )
                            future.result()
                            logger.bind(tag=TAG).info("TTS文本发送成功")
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"发送TTS文本失败: {str(e)}")
                            # 直接跳过当前消息，不重新入队
                            time.sleep(1)
                            continue
                elif ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(
                        f"添加音频文件到待播放列表: {message.content_file}"
                    )
                    self.before_stop_play_files.append(
                        (message.content_file, message.content_detail)
                    )

                if message.sentence_type == SentenceType.LAST:
                    try:
                        logger.bind(tag=TAG).info("开始结束TTS会话...")
                        future = asyncio.run_coroutine_threadsafe(
                            self.finish_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                        future.result()
                        logger.bind(tag=TAG).info("TTS会话结束成功")
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"结束TTS会话失败: {str(e)}")
                        # 直接跳过当前消息，不重新入队
                        time.sleep(1)
                        continue

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理TTS文本失败: {str(e)}, 类型: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )
                # 如果是WebSocket连接关闭错误，等待一段时间后继续
                if "non-exist session" in str(e):
                    time.sleep(1)
                continue

    async def text_to_speak(self, text, _):
        """发送文本到TTS服务"""
        try:
            # 确保WebSocket连接可用
            if not self._connection_ready or self.ws is None:
                logger.bind(tag=TAG).warning("WebSocket连接不可用，尝试重新连接...")
                await self._ensure_connection()

            # 发送文本
            await self.send_text(self.speaker, text, self.conn.sentence_id)
            return
        except Exception as e:
            logger.bind(tag=TAG).error(f"发送TTS文本失败: {str(e)}")
            # 如果是连接问题，尝试重新连接
            if isinstance(e, websockets.ConnectionClosed):
                self._connection_ready = False
                self.ws = None
                await self._handle_connection_error()
            raise

    ###################################################################################
    # 火山双流式TTS重写父类的方法--结束
    ###################################################################################
    def _start_monitor_tts_response_thread(self):
        # 初始化链接
        asyncio.run_coroutine_threadsafe(
            self._start_monitor_tts_response(), loop=self.conn.loop
        )

    async def _start_monitor_tts_response(self):
        opus_datas_cache = []
        # 添加标志来区分是否是第一句话
        is_first_sentence = True
        while not self.conn.stop_event.is_set():
            try:
                # 确保 `recv()` 运行在同一个 event loop
                msg = await self.ws.recv()
                res = self.parser_response(msg)
                self.print_response(res, "send_text res:")

                if res.optional.event == EVENT_TTSSentenceStart:
                    json_data = json.loads(res.payload.decode("utf-8"))
                    self.tts_text = json_data.get("text", "")
                    logger.bind(tag=TAG).debug(f"句子语音生成开始: {self.tts_text}")
                    self.tts_audio_queue.put((SentenceType.FIRST, [], self.tts_text))
                    opus_datas_cache = []
                elif (
                    res.optional.event == EVENT_TTSResponse
                    and res.header.message_type == AUDIO_ONLY_RESPONSE
                ):
                    logger.bind(tag=TAG).debug(f"推送数据到队列里面～～")
                    opus_datas = self.wav_to_opus_data_audio_raw(res.payload)
                    logger.bind(tag=TAG).debug(
                        f"推送数据到队列里面帧数～～{len(opus_datas)}"
                    )
                    if is_first_sentence:
                        # 第一句话直接发送
                        self.tts_audio_queue.put(
                            (SentenceType.MIDDLE, opus_datas, self.tts_text)
                        )
                    else:
                        # 后续句子缓存
                        opus_datas_cache = opus_datas_cache + opus_datas
                elif res.optional.event == EVENT_TTSSentenceEnd:
                    logger.bind(tag=TAG).info(f"句子语音生成成功：{self.tts_text}")
                    if not is_first_sentence:
                        # 只有非第一句话才发送缓存的数据
                        self.tts_audio_queue.put(
                            (SentenceType.MIDDLE, opus_datas_cache, self.tts_text)
                        )
                    # 第一句话结束后，将标志设置为False
                    is_first_sentence = False
                elif res.optional.event == EVENT_SessionFinished:
                    logger.bind(tag=TAG).debug(f"会话结束～～")
                    for tts_file, text in self.before_stop_play_files:
                        if tts_file and os.path.exists(tts_file):
                            audio_datas = self._process_audio_file(tts_file)
                            self.tts_audio_queue.put(
                                (SentenceType.MIDDLE, audio_datas, text)
                            )
                    self.before_stop_play_files.clear()
                    self.tts_audio_queue.put((SentenceType.LAST, [], None))

                    opus_datas_cache = []
                    is_first_sentence = True
                    continue
            except websockets.ConnectionClosed:
                break  # 连接关闭时退出监听
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error in _start_monitor_tts_response: {e}")
                traceback.print_exc()
                continue

    async def send_event(
        self, header: bytes, optional: bytes | None = None, payload: bytes = None
    ):
        try:
            full_client_request = bytearray(header)
            if optional is not None:
                full_client_request.extend(optional)
            if payload is not None:
                payload_size = len(payload).to_bytes(4, "big", signed=True)
                full_client_request.extend(payload_size)
                full_client_request.extend(payload)
            await self.ws.send(full_client_request)
        except websockets.ConnectionClosed:
            if await self._handle_connection_error():
                # 重连成功后重试发送
                await self.ws.send(full_client_request)
            else:
                raise

    async def send_text(self, speaker: str, text: str, session_id):
        header = Header(
            message_type=FULL_CLIENT_REQUEST,
            message_type_specific_flags=MsgTypeFlagWithEvent,
            serial_method=JSON,
        ).as_bytes()
        optional = Optional(event=EVENT_TaskRequest, sessionId=session_id).as_bytes()
        payload = self.get_payload_bytes(
            event=EVENT_TaskRequest, text=text, speaker=speaker
        )
        return await self.send_event(header, optional, payload)

    # 读取 res 数组某段 字符串内容
    def read_res_content(self, res: bytes, offset: int):
        content_size = int.from_bytes(res[offset : offset + 4], "big", signed=True)
        offset += 4
        content = str(res[offset : offset + content_size])
        offset += content_size
        return content, offset

    # 读取 payload
    def read_res_payload(self, res: bytes, offset: int):
        payload_size = int.from_bytes(res[offset : offset + 4], "big", signed=True)
        offset += 4
        payload = res[offset : offset + payload_size]
        offset += payload_size
        return payload, offset

    def parser_response(self, res) -> Response:
        if isinstance(res, str):
            raise RuntimeError(res)
        response = Response(Header(), Optional())
        # 解析结果
        # header
        header = response.header
        num = 0b00001111
        header.protocol_version = res[0] >> 4 & num
        header.header_size = res[0] & 0x0F
        header.message_type = (res[1] >> 4) & num
        header.message_type_specific_flags = res[1] & 0x0F
        header.serialization_method = res[2] >> num
        header.message_compression = res[2] & 0x0F
        header.reserved = res[3]
        #
        offset = 4
        optional = response.optional
        if header.message_type == FULL_SERVER_RESPONSE or AUDIO_ONLY_RESPONSE:
            # read event
            if header.message_type_specific_flags == MsgTypeFlagWithEvent:
                optional.event = int.from_bytes(res[offset:8], "big", signed=True)
                offset += 4
                if optional.event == EVENT_NONE:
                    return response
                # read connectionId
                elif optional.event == EVENT_ConnectionStarted:
                    optional.connectionId, offset = self.read_res_content(res, offset)
                elif optional.event == EVENT_ConnectionFailed:
                    optional.response_meta_json, offset = self.read_res_content(
                        res, offset
                    )
                elif (
                    optional.event == EVENT_SessionStarted
                    or optional.event == EVENT_SessionFailed
                    or optional.event == EVENT_SessionFinished
                ):
                    optional.sessionId, offset = self.read_res_content(res, offset)
                    optional.response_meta_json, offset = self.read_res_content(
                        res, offset
                    )
                else:
                    optional.sessionId, offset = self.read_res_content(res, offset)
                    response.payload, offset = self.read_res_payload(res, offset)

        elif header.message_type == ERROR_INFORMATION:
            optional.errorCode = int.from_bytes(
                res[offset : offset + 4], "big", signed=True
            )
            offset += 4
            response.payload, offset = self.read_res_payload(res, offset)
        return response

    async def start_connection(self):
        header = Header(
            message_type=FULL_CLIENT_REQUEST,
            message_type_specific_flags=MsgTypeFlagWithEvent,
        ).as_bytes()
        optional = Optional(event=EVENT_Start_Connection).as_bytes()
        payload = str.encode("{}")
        return await self.send_event(header, optional, payload)

    def print_response(self, res, tag_msg: str):
        logger.bind(tag=TAG).debug(f"===>{tag_msg} header:{res.header.__dict__}")
        logger.bind(tag=TAG).debug(f"===>{tag_msg} optional:{res.optional.__dict__}")

    def get_payload_bytes(
        self,
        uid="1234",
        event=EVENT_NONE,
        text="",
        speaker="",
        audio_format="pcm",
        audio_sample_rate=16000,
    ):
        return str.encode(
            json.dumps(
                {
                    "user": {"uid": uid},
                    "event": event,
                    "namespace": "BidirectionalTTS",
                    "req_params": {
                        "text": text,
                        "speaker": speaker,
                        "audio_params": {
                            "format": audio_format,
                            "sample_rate": audio_sample_rate,
                        },
                    },
                }
            )
        )

    async def finish_connection(self):
        header = Header(
            message_type=FULL_CLIENT_REQUEST,
            message_type_specific_flags=MsgTypeFlagWithEvent,
            serial_method=JSON,
        ).as_bytes()
        optional = Optional(event=EVENT_FinishConnection).as_bytes()
        payload = str.encode("{}")
        await self.send_event(header, optional, payload)
        return

    async def start_session(self, session_id):
        logger.bind(tag=TAG).info(f"开始会话～～{session_id}")
        try:
            async with self._session_lock:
                try:
                    # 确保连接可用
                    logger.bind(tag=TAG).info("检查WebSocket连接状态...")
                    await asyncio.wait_for(self._ensure_connection(), timeout=5)

                    # 如果已有会话未结束，先关闭它
                    if self._session_started and not self._session_finished:
                        logger.bind(tag=TAG).warning(
                            f"发现未关闭的会话 {self._current_session_id}，正在关闭..."
                        )
                        try:
                            await asyncio.wait_for(
                                self.finish_session(self._current_session_id), timeout=5
                            )
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"关闭旧会话失败: {str(e)}")
                            # 强制重置会话状态
                            self._session_started = False
                            self._session_finished = True
                            self._current_session_id = None

                    # 重置会话状态
                    self._current_session_id = session_id
                    self._session_started = True
                    self._session_finished = False
                    logger.bind(tag=TAG).info(
                        f"会话状态已更新 - 开始: {self._session_started}, 结束: {self._session_finished}"
                    )

                    header = Header(
                        message_type=FULL_CLIENT_REQUEST,
                        message_type_specific_flags=MsgTypeFlagWithEvent,
                        serial_method=JSON,
                    ).as_bytes()
                    optional = Optional(
                        event=EVENT_StartSession, sessionId=session_id
                    ).as_bytes()
                    payload = self.get_payload_bytes(
                        event=EVENT_StartSession, speaker=self.speaker
                    )
                    await asyncio.wait_for(
                        self.send_event(header, optional, payload), timeout=5
                    )
                    logger.bind(tag=TAG).info("会话启动请求已发送")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"启动会话失败: {str(e)}")
                    self._session_started = False
                    self._session_finished = True
                    self._current_session_id = None
                    raise
        except asyncio.TimeoutError:
            logger.bind(tag=TAG).error(f"启动会话超时: {session_id}")
            # 超时后强制重置会话状态
            self._session_started = False
            self._session_finished = True
            self._current_session_id = None
            # 尝试关闭WebSocket连接
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
        except Exception as e:
            logger.bind(tag=TAG).error(f"启动会话时发生未知错误: {str(e)}")
            # 发生未知错误时也重置会话状态
            self._session_started = False
            self._session_finished = True
            self._current_session_id = None

    async def finish_session(self, session_id):
        logger.bind(tag=TAG).info(f"关闭会话～～{session_id}")
        try:
            async with self._session_lock:
                try:
                    # 检查会话状态
                    if not self._session_started:
                        logger.bind(tag=TAG).warning(
                            f"尝试关闭未开始的会话 {session_id}"
                        )
                        return

                    if self._session_finished:
                        logger.bind(tag=TAG).warning(f"会话 {session_id} 已经关闭")
                        return

                    if self._current_session_id != session_id:
                        logger.bind(tag=TAG).warning(
                            f"尝试关闭错误的会话 {session_id}，当前会话为 {self._current_session_id}"
                        )
                        # 即使会话ID不匹配，也尝试关闭当前会话
                        if self._current_session_id:
                            session_id = self._current_session_id

                    # 确保WebSocket连接可用
                    if self.ws is None:
                        logger.bind(tag=TAG).warning(
                            "WebSocket连接不存在，尝试重新连接..."
                        )
                        await asyncio.wait_for(self._ensure_connection(), timeout=5)

                    header = Header(
                        message_type=FULL_CLIENT_REQUEST,
                        message_type_specific_flags=MsgTypeFlagWithEvent,
                        serial_method=JSON,
                    ).as_bytes()
                    optional = Optional(
                        event=EVENT_FinishSession, sessionId=session_id
                    ).as_bytes()
                    payload = str.encode("{}")
                    await asyncio.wait_for(
                        self.send_event(header, optional, payload), timeout=5
                    )
                    logger.bind(tag=TAG).info("会话结束请求已发送")

                    # 更新会话状态
                    self._session_finished = True
                    self._session_started = False
                    self._current_session_id = None
                    logger.bind(tag=TAG).info(
                        "会话状态已更新 - 开始: False, 结束: True"
                    )
                except Exception as e:
                    logger.bind(tag=TAG).error(f"关闭会话失败: {str(e)}")
                    # 即使发生错误，也要重置会话状态
                    self._session_finished = True
                    self._session_started = False
                    self._current_session_id = None
                    raise
        except asyncio.TimeoutError:
            logger.bind(tag=TAG).error(f"关闭会话超时: {session_id}")
            # 超时后强制重置会话状态
            self._session_finished = True
            self._session_started = False
            self._current_session_id = None
            # 尝试关闭WebSocket连接
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
        except Exception as e:
            logger.bind(tag=TAG).error(f"关闭会话时发生未知错误: {str(e)}")
            # 发生未知错误时也重置会话状态
            self._session_finished = True
            self._session_started = False
            self._current_session_id = None

    async def reset(self):
        # 关闭之前的对话
        if self.start_connection_flag:
            await self.finish_connection()
            self.start_connection_flag = False
        await self.start_connection()
        self.start_connection_flag = True

    async def close(self):
        """资源清理方法"""
        await self.finish_connection()
        await self.ws.close()

    def wav_to_opus_data_audio_raw(self, raw_data_var, is_end=False):
        opus_datas = self.opus_encoder.encode_pcm_to_opus(raw_data_var, is_end)
        return opus_datas

    async def _handle_connection_error(self):
        """处理连接错误"""
        if self._reconnect_attempts < self._max_reconnect_attempts:
            self._reconnect_attempts += 1
            logger.bind(tag=TAG).warning(
                f"尝试重新连接 (第{self._reconnect_attempts}次)"
            )
            try:
                await self._ensure_connection()
                return True
            except Exception as e:
                logger.bind(tag=TAG).error(f"重新连接失败: {str(e)}")
                return False
        else:
            logger.bind(tag=TAG).error("达到最大重连次数，放弃重连")
            return False
