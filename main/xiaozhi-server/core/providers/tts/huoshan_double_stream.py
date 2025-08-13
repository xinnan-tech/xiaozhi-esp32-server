import os
import uuid
import json
import queue
import asyncio
import traceback
import websockets
from core.utils.tts import MarkdownCleaner
from config.logger import setup_logging
from core.utils import opus_encoder_utils
from core.utils.util import check_model_key
from core.providers.tts.base import TTSProviderBase
from core.handle.abortHandle import handleAbortMessage
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType
from asyncio import Task

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
EVENT_ConnectionStarted = 50  # Successful connection
# Connection failed (possibly unable to pass permission authentication)
EVENT_ConnectionFailed = 51
EVENT_ConnectionFinished = 52  # Connection ended

# Uplink Session events

EVENT_StartSession = 100
EVENT_FinishSession = 102

# Downlink Session events

EVENT_SessionStarted = 150
EVENT_SessionFinished = 152
EVENT_SessionFailed = 153

# Uplink general events

EVENT_TaskRequest = 200

# Downlink TTS events

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

    # Convert to byte sequence

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

        self.ws = None

        self.interface_type = InterfaceType.DUAL_STREAM

        self._monitor_task = None  # Monitor task reference

        self.appId = config.get("appid")

        self.access_token = config.get("access_token")

        self.cluster = config.get("cluster")

        self.resource_id = config.get("resource_id")

        if config.get("private_voice"):

            self.voice = config.get("private_voice")

        else:

            self.voice = config.get("speaker")

        self.ws_url = config.get("ws_url")

        self.authorization = config.get("authorization")

        self.header = {
            "Authorization": f"{self.authorization}{self.access_token}"}

        self.enable_two_way = True

        self.tts_text = ""

        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(

            sample_rate=16000, channels=1, frame_size_ms=60

        )

        model_key_msg = check_model_key("TTS", self.access_token)

        if model_key_msg:

            logger.bind(tag=TAG).error(model_key_msg)

    async def open_audio_channels(self, conn):

        try:

            await super().open_audio_channels(conn)

        except Exception as e:

            logger.bind(tag=TAG).error(
                f"Failed to open audio channels: {str(e)}")

            self.ws = None

            raise

    async def _ensure_connection(self):
        """Establish new WebSocket connection"""

        try:

            logger.bind(tag=TAG).info(
                "Starting to establish new connection...")

            ws_header = {

                "X-Api-App-Key": self.appId,

                "X-Api-Access-Key": self.access_token,

                "X-Api-Resource-Id": self.resource_id,

                "X-Api-Connect-Id": uuid.uuid4(),

            }

            self.ws = await websockets.connect(

                self.ws_url, additional_headers=ws_header, max_size=1000000000

            )

            logger.bind(tag=TAG).info(
                "WebSocket connection established successfully")

            return self.ws

        except Exception as e:

            logger.bind(tag=TAG).error(
                f"Failed to establish connection: {str(e)}")

            self.ws = None

            raise

    def tts_text_priority_thread(self):
        """Volcano Engine dual-stream TTS text processing thread"""

        while not self.conn.stop_event.is_set():

            try:

                message = self.tts_text_queue.get(timeout=1)

                logger.bind(tag=TAG).debug(

                    f"Received TTS task | {message.sentence_type.name} | {message.content_type.name} | Session ID: {self.conn.sentence_id}"

                )

                if self.conn.client_abort:

                    logger.bind(tag=TAG).info(
                        "Received interruption signal, terminating TTS text processing thread")

                    continue

                if message.sentence_type == SentenceType.FIRST:

                    # Initialize parameters

                    try:

                        if not getattr(self.conn, "sentence_id", None):

                            self.conn.sentence_id = uuid.uuid4().hex

                            logger.bind(tag=TAG).info(
                                f"Auto-generated new session ID: {self.conn.sentence_id}")

                        logger.bind(tag=TAG).info("Starting TTS session...")

                        future = asyncio.run_coroutine_threadsafe(

                            self.start_session(self.conn.sentence_id),

                            loop=self.conn.loop,

                        )

                        future.result()

                        self.tts_audio_first_sentence = True

                        self.before_stop_play_files.clear()

                        logger.bind(tag=TAG).info(
                            "TTS session started successfully")

                    except Exception as e:

                        logger.bind(tag=TAG).error(
                            f"Failed to start TTS session: {str(e)}")

                        continue

                elif ContentType.TEXT == message.content_type:

                    if message.content_detail:

                        try:

                            logger.bind(tag=TAG).debug(

                                f"Starting to send TTS text: {message.content_detail}"

                            )

                            future = asyncio.run_coroutine_threadsafe(

                                self.text_to_speak(
                                    message.content_detail, None),

                                loop=self.conn.loop,

                            )

                            future.result()

                            logger.bind(tag=TAG).debug(
                                "TTS text sent successfully")

                        except Exception as e:

                            logger.bind(tag=TAG).error(
                                f"Failed to send TTS text: {str(e)}")

                            continue

                elif ContentType.FILE == message.content_type:

                    logger.bind(tag=TAG).info(

                        f"Adding audio file to playback queue: {message.content_file}"

                    )

                    self.before_stop_play_files.append(

                        (message.content_file, message.content_detail)

                    )

                if message.sentence_type == SentenceType.LAST:

                    try:

                        logger.bind(tag=TAG).info(
                            "Starting to end TTS session...")

                        future = asyncio.run_coroutine_threadsafe(

                            self.finish_session(self.conn.sentence_id),

                            loop=self.conn.loop,

                        )

                        future.result()

                    except Exception as e:

                        logger.bind(tag=TAG).error(
                            f"Failed to end TTS session: {str(e)}")

                        continue

            except queue.Empty:

                continue

            except Exception as e:

                logger.bind(tag=TAG).error(

                    f"Failed to process TTS text: {str(e)}, type: {type(e).__name__}, stack: {traceback.format_exc()}"

                )

                continue

    async def text_to_speak(self, text, _):
        """Send text to TTS service"""

        try:

            # Establish new connection

            if self.ws is None:

                logger.bind(tag=TAG).warning(
                    f"WebSocket connection does not exist, terminating text sending")

                return

            # Filter Markdown

            filtered_text = MarkdownCleaner.clean_markdown(text)

            # Send text

            await self.send_text(self.voice, filtered_text, self.conn.sentence_id)

            return

        except Exception as e:

            logger.bind(tag=TAG).error(f"Failed to send TTS text: {str(e)}")

            if self.ws:

                try:

                    await self.ws.close()

                except:

                    pass

            self.ws = None

            raise

    async def start_session(self, session_id):

        logger.bind(tag=TAG).info(f"Starting session ~~ {session_id}")

        try:

            task = self._monitor_task

            if (

                task is not None

                and isinstance(task, Task)

                and not task.done()

            ):

                logger.bind(tag=TAG).info(
                    "Waiting for previous monitor task to end...")

                if self.ws is not None:

                    logger.bind(tag=TAG).info(
                        "Forcing close of previous WebSocket connection to wake up monitor task...")

                    try:

                        await self.ws.close()

                    except Exception as e:

                        logger.bind(tag=TAG).warning(
                            f"Exception closing previous ws: {e}")

                    self.ws = None

                try:

                    await asyncio.wait_for(task, timeout=8)

                except Exception as e:

                    logger.bind(tag=TAG).warning(
                        f"Exception waiting for monitor task: {e}")

                self._monitor_task = None

            # Establish new connection

            await self._ensure_connection()

            # Start monitor task

            self._monitor_task = asyncio.create_task(
                self._start_monitor_tts_response())

            header = Header(

                message_type=FULL_CLIENT_REQUEST,

                message_type_specific_flags=MsgTypeFlagWithEvent,

                serial_method=JSON,

            ).as_bytes()

            optional = Optional(

                event=EVENT_StartSession, sessionId=session_id

            ).as_bytes()

            payload = self.get_payload_bytes(

                event=EVENT_StartSession, speaker=self.voice

            )

            await self.send_event(self.ws, header, optional, payload)

            logger.bind(tag=TAG).info("Session start request sent")

        except Exception as e:

            logger.bind(tag=TAG).error(f"Failed to start session: {str(e)}")

            # Ensure resource cleanup

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

        logger.bind(tag=TAG).info(f"Closing session ~~ {session_id}")

        try:

            if self.ws:

                header = Header(

                    message_type=FULL_CLIENT_REQUEST,

                    message_type_specific_flags=MsgTypeFlagWithEvent,

                    serial_method=JSON,

                ).as_bytes()

                optional = Optional(

                    event=EVENT_FinishSession, sessionId=session_id

                ).as_bytes()

                payload = str.encode("{}")

                await self.send_event(self.ws, header, optional, payload)

                logger.bind(tag=TAG).info("Session end request sent")

                # Wait for monitor task to complete

                if hasattr(self, "_monitor_task"):

                    try:

                        await self._monitor_task

                    except Exception as e:

                        logger.bind(tag=TAG).error(

                            f"Error occurred while waiting for monitor task completion: {str(e)}"

                        )

                    finally:

                        self._monitor_task = None

                # Close connection

                await self.close()

        except Exception as e:

            logger.bind(tag=TAG).error(f"Failed to close session: {str(e)}")

            # Ensure resource cleanup

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

    async def close(self):
        """Resource cleanup method"""

        if self.ws:

            try:

                await self.ws.close()

            except:

                pass

            self.ws = None

    async def _start_monitor_tts_response(self):
        """Monitor TTS responses"""

        opus_datas_cache = []

        is_first_sentence = True

        first_sentence_segment_count = 0  # Add counter

        try:

            while not self.conn.stop_event.is_set():

                try:

                    # Ensure `recv()` runs on the same event loop

                    msg = await self.ws.recv()

                    res = self.parser_response(msg)

                    self.print_response(res, "send_text res:")

                    # Check if client aborted

                    if self.conn.client_abort:

                        logger.bind(tag=TAG).info(
                            "Received interruption signal, terminating TTS response monitoring")

                        break

                    if res.optional.event == EVENT_TTSSentenceStart:

                        json_data = json.loads(res.payload.decode("utf-8"))

                        self.tts_text = json_data.get("text", "")

                        logger.bind(tag=TAG).debug(
                            f"Sentence voice generation started: {self.tts_text}")

                        self.tts_audio_queue.put(

                            (SentenceType.FIRST, [], self.tts_text)

                        )

                        opus_datas_cache = []

                        first_sentence_segment_count = 0  # Reset counter

                    elif (

                        res.optional.event == EVENT_TTSResponse

                        and res.header.message_type == AUDIO_ONLY_RESPONSE

                    ):

                        logger.bind(tag=TAG).debug(f"Pushing data to queue ~~")

                        opus_datas = self.wav_to_opus_data_audio_raw(
                            res.payload)

                        logger.bind(tag=TAG).debug(

                            f"Pushing data to queue frame count ~~ {len(opus_datas)}"

                        )

                        if is_first_sentence:

                            first_sentence_segment_count += 1

                            if first_sentence_segment_count <= 6:

                                self.tts_audio_queue.put(

                                    (SentenceType.MIDDLE, opus_datas, None)

                                )

                            else:

                                opus_datas_cache = opus_datas_cache + opus_datas

                        else:

                            # Cache subsequent sentences

                            opus_datas_cache = opus_datas_cache + opus_datas

                    elif res.optional.event == EVENT_TTSSentenceEnd:

                        logger.bind(tag=TAG).info(
                            f"Sentence voice generation successful: {self.tts_text}")

                        if not is_first_sentence or first_sentence_segment_count > 10:

                            # Send cached data

                            self.tts_audio_queue.put(

                                (SentenceType.MIDDLE, opus_datas_cache, None)

                            )

                        # After first sentence ends, set flag to False

                        is_first_sentence = False

                    elif res.optional.event == EVENT_SessionFinished:

                        logger.bind(tag=TAG).debug(f"Session ended ~~")

                        self._process_before_stop_play_files()

                        break

                except websockets.ConnectionClosed:

                    logger.bind(tag=TAG).warning("WebSocket connection closed")

                    break

                except Exception as e:

                    logger.bind(tag=TAG).error(

                        f"Error in _start_monitor_tts_response: {e}"

                    )

                    traceback.print_exc()

                    break

        finally:

            # Ensure resource cleanup

            if self.ws:

                try:

                    await self.ws.close()

                except:

                    pass

                self.ws = None

            # Clear reference when monitor task exits

            self._monitor_task = None

    async def send_event(

        self,

        ws: websockets.WebSocketClientProtocol,

        header: bytes,

        optional: bytes | None = None,

        payload: bytes = None,

    ):

        try:

            full_client_request = bytearray(header)

            if optional is not None:

                full_client_request.extend(optional)

            if payload is not None:

                payload_size = len(payload).to_bytes(4, "big", signed=True)

                full_client_request.extend(payload_size)

                full_client_request.extend(payload)

            await ws.send(full_client_request)

        except websockets.ConnectionClosed:

            logger.bind(tag=TAG).error(f"ConnectionClosed")

            raise

    async def send_text(self, speaker: str, text: str, session_id):

        header = Header(

            message_type=FULL_CLIENT_REQUEST,

            message_type_specific_flags=MsgTypeFlagWithEvent,

            serial_method=JSON,

        ).as_bytes()

        optional = Optional(event=EVENT_TaskRequest,
                            sessionId=session_id).as_bytes()

        payload = self.get_payload_bytes(

            event=EVENT_TaskRequest, text=text, speaker=speaker

        )

        return await self.send_event(self.ws, header, optional, payload)

    # Read res array segment string content

    def read_res_content(self, res: bytes, offset: int):

        content_size = int.from_bytes(
            res[offset: offset + 4], "big", signed=True)

        offset += 4

        content = str(res[offset: offset + content_size])

        offset += content_size

        return content, offset

    # Read payload

    def read_res_payload(self, res: bytes, offset: int):

        payload_size = int.from_bytes(
            res[offset: offset + 4], "big", signed=True)

        offset += 4

        payload = res[offset: offset + payload_size]

        offset += payload_size

        return payload, offset

    def parser_response(self, res) -> Response:

        if isinstance(res, str):

            raise RuntimeError(res)

        response = Response(Header(), Optional())

        # Parse result

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

        offset = 4

        optional = response.optional

        if header.message_type == FULL_SERVER_RESPONSE or AUDIO_ONLY_RESPONSE:

            # read event

            if header.message_type_specific_flags == MsgTypeFlagWithEvent:

                optional.event = int.from_bytes(
                    res[offset:8], "big", signed=True)

                offset += 4

                if optional.event == EVENT_NONE:

                    return response

                # read connectionId

                elif optional.event == EVENT_ConnectionStarted:

                    optional.connectionId, offset = self.read_res_content(
                        res, offset)

                elif optional.event == EVENT_ConnectionFailed:

                    optional.response_meta_json, offset = self.read_res_content(

                        res, offset

                    )

                elif (

                    optional.event == EVENT_SessionStarted

                    or optional.event == EVENT_SessionFailed

                    or optional.event == EVENT_SessionFinished

                ):

                    optional.sessionId, offset = self.read_res_content(
                        res, offset)

                    optional.response_meta_json, offset = self.read_res_content(

                        res, offset

                    )

                else:

                    optional.sessionId, offset = self.read_res_content(
                        res, offset)

                response.payload, offset = self.read_res_payload(res, offset)

        elif header.message_type == ERROR_INFORMATION:

            optional.errorCode = int.from_bytes(

                res[offset: offset + 4], "big", signed=True

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

        return await self.send_event(self.ws, header, optional, payload)

    def print_response(self, res, tag_msg: str):

        logger.bind(tag=TAG).debug(
            f"===> {tag_msg} header:{res.header.__dict__}")

        logger.bind(tag=TAG).debug(
            f"===> {tag_msg} optional:{res.optional.__dict__}")

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

    def wav_to_opus_data_audio_raw(self, raw_data_var, is_end=False):

        opus_datas = self.opus_encoder.encode_pcm_to_opus(raw_data_var, is_end)

        return opus_datas

    def to_tts(self, text: str) -> list:
        """Non-streaming audio data generation for audio generation and testing scenarios

        Args:

            text: Text to convert

        Returns:

            list: Audio data list

        """

        try:

            # Create event loop

            loop = asyncio.new_event_loop()

            asyncio.set_event_loop(loop)

            # Generate session ID

            session_id = uuid.uuid4().__str__().replace("-", "")

            # Store audio data

            audio_data = []

            async def _generate_audio():

                # Create new WebSocket connection

                ws_header = {

                    "X-Api-App-Key": self.appId,

                    "X-Api-Access-Key": self.access_token,

                    "X-Api-Resource-Id": self.resource_id,

                    "X-Api-Connect-Id": uuid.uuid4(),

                }

                ws = await websockets.connect(

                    self.ws_url, additional_headers=ws_header, max_size=1000000000

                )

                try:

                    # Start session

                    header = Header(

                        message_type=FULL_CLIENT_REQUEST,

                        message_type_specific_flags=MsgTypeFlagWithEvent,

                        serial_method=JSON,

                    ).as_bytes()

                    optional = Optional(

                        event=EVENT_StartSession, sessionId=session_id

                    ).as_bytes()

                    payload = self.get_payload_bytes(

                        event=EVENT_StartSession, speaker=self.voice

                    )

                    await self.send_event(ws, header, optional, payload)

                    # Send text

                    header = Header(

                        message_type=FULL_CLIENT_REQUEST,

                        message_type_specific_flags=MsgTypeFlagWithEvent,

                        serial_method=JSON,

                    ).as_bytes()

                    optional = Optional(

                        event=EVENT_TaskRequest, sessionId=session_id

                    ).as_bytes()

                    payload = self.get_payload_bytes(

                        event=EVENT_TaskRequest, text=text, speaker=self.voice

                    )

                    await self.send_event(ws, header, optional, payload)

                    # Send session end request

                    header = Header(

                        message_type=FULL_CLIENT_REQUEST,

                        message_type_specific_flags=MsgTypeFlagWithEvent,

                        serial_method=JSON,

                    ).as_bytes()

                    optional = Optional(

                        event=EVENT_FinishSession, sessionId=session_id

                    ).as_bytes()

                    payload = str.encode("{}")

                    await self.send_event(ws, header, optional, payload)

                    # Receive audio data

                    while True:

                        msg = await ws.recv()

                        res = self.parser_response(msg)

                        if (

                            res.optional.event == EVENT_TTSResponse

                            and res.header.message_type == AUDIO_ONLY_RESPONSE

                        ):

                            opus_datas = self.wav_to_opus_data_audio_raw(
                                res.payload)

                            audio_data.extend(opus_datas)

                        elif res.optional.event == EVENT_SessionFinished:

                            break

                finally:

                    # Cleanup resources

                    try:

                        await ws.close()

                    except:

                        pass

            # Run async task

            loop.run_until_complete(_generate_audio())

            loop.close()

            return audio_data

        except Exception as e:

            logger.bind(tag=TAG).error(
                f"Failed to generate audio data: {str(e)}")

            return []
