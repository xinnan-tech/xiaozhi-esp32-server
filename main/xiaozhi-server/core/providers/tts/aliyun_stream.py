import uuid
import json
import hmac
import hashlib
import base64
import time
import queue
import asyncio
import traceback
from asyncio import Task
import websockets
import os
from datetime import datetime
from urllib import parse
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType
from core.utils.tts import MarkdownCleaner
from core.utils import opus_encoder_utils, textUtils
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class AccessToken:
    @staticmethod
    def _encode_text(text):
        encoded_text = parse.quote_plus(text)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def _encode_dict(dic):
        keys = dic.keys()
        dic_sorted = [(key, dic[key]) for key in sorted(keys)]
        encoded_text = parse.urlencode(dic_sorted)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def create_token(access_key_id, access_key_secret):
        parameters = {
            "AccessKeyId": access_key_id,
            "Action": "CreateToken",
            "Format": "JSON",
            "RegionId": "cn-shanghai",  # Use Shanghai region for Token acquisition
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid1()),
            "SignatureVersion": "1.0",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "Version": "2019-02-28",
        }

        query_string = AccessToken._encode_dict(parameters)
        string_to_sign = (
            "GET"
            + "&"
            + AccessToken._encode_text("/")
            + "&"
            + AccessToken._encode_text(query_string)
        )

        secreted_string = hmac.new(
            bytes(access_key_secret + "&", encoding="utf-8"),
            bytes(string_to_sign, encoding="utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(secreted_string)
        signature = AccessToken._encode_text(signature)

        full_url = "http://nls-meta.cn-shanghai.aliyuncs.com/?Signature=%s&%s" % (
            signature,
            query_string,
        )

        import requests

        response = requests.get(full_url)
        if response.ok:
            root_obj = response.json()
            key = "Token"
            if key in root_obj:
                token = root_obj[key]["Id"]
                expire_time = root_obj[key]["ExpireTime"]
                return token, expire_time
        return None, None


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)

        # Set to streaming interface type
        self.interface_type = InterfaceType.DUAL_STREAM

        # Basic configuration
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")
        self.appkey = config.get("appkey")
        self.format = config.get("format", "pcm")
        self.audio_file_type = config.get("format", "pcm")

        # Sample rate configuration
        sample_rate = config.get("sample_rate", "16000")
        self.sample_rate = int(sample_rate) if sample_rate else 16000

        # Voice configuration - CosyVoice large model voice
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            # CosyVoice default voice
            self.voice = config.get("voice", "longxiaochun")

        # Audio parameter configuration
        volume = config.get("volume", "50")
        self.volume = int(volume) if volume else 50

        speech_rate = config.get("speech_rate", "0")
        self.speech_rate = int(speech_rate) if speech_rate else 0

        pitch_rate = config.get("pitch_rate", "0")
        self.pitch_rate = int(pitch_rate) if pitch_rate else 0

        # WebSocket configuration
        self.host = config.get("host", "nls-gateway-cn-beijing.aliyuncs.com")
        # If configured with internal network address (contains -internal.aliyuncs.com), use ws protocol, default is wss protocol
        if "-internal." in self.host:
            self.ws_url = f"ws://{self.host}/ws/v1"
        else:
            # Default to wss protocol
            self.ws_url = f"wss://{self.host}/ws/v1"
        self.ws = None
        self._monitor_task = None
        self.last_active_time = None

        # Dedicated TTS settings
        self.message_id = ""

        # Create Opus encoder
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=16000, channels=1, frame_size_ms=60
        )

        # Token management
        if self.access_key_id and self.access_key_secret:
            self._refresh_token()
        else:
            self.token = config.get("token")
            self.expire_time = None

    def _refresh_token(self):
        """Refresh Token and record expiration time"""
        if self.access_key_id and self.access_key_secret:
            self.token, expire_time_str = AccessToken.create_token(
                self.access_key_id, self.access_key_secret
            )
            if not expire_time_str:
                raise ValueError("Unable to get valid Token expiration time")

            expire_str = str(expire_time_str).strip()

            try:
                if expire_str.isdigit():
                    expire_time = datetime.fromtimestamp(int(expire_str))
                else:
                    expire_time = datetime.strptime(
                        expire_str, "%Y-%m-%dT%H:%M:%SZ")
                self.expire_time = expire_time.timestamp() - 60
            except Exception as e:
                raise ValueError(
                    f"Invalid expiration time format: {expire_str}") from e
        else:
            self.expire_time = None

        if not self.token:
            raise ValueError("Unable to get valid access Token")

    def _is_token_expired(self):
        """Check if Token is expired"""
        if not self.expire_time:
            return False
        return time.time() > self.expire_time

    async def _ensure_connection(self):
        """Ensure WebSocket connection is available"""
        try:
            if self._is_token_expired():
                logger.bind(tag=TAG).warning(
                    "Token has expired, automatically refreshing...")
                self._refresh_token()
            current_time = time.time()
            if self.ws and current_time - self.last_active_time < 10:
                # Can only reuse connection for continuous conversation within 10 seconds
                logger.bind(tag=TAG).info(f"Using existing connection...")
                return self.ws
            logger.bind(tag=TAG).info(
                "Starting to establish new connection...")

            self.ws = await websockets.connect(
                self.ws_url,
                additional_headers={"X-NLS-Token": self.token},
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10,
            )
            logger.bind(tag=TAG).info(
                "WebSocket connection established successfully")
            self.last_active_time = time.time()
            return self.ws
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Failed to establish connection: {str(e)}")
            self.ws = None
            self.last_active_time = None
            raise

    def tts_text_priority_thread(self):
        """Streaming text processing thread"""
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                logger.bind(tag=TAG).debug(
                    f"Received TTS task｜{message.sentence_type.name} ｜ {message.content_type.name} | Session ID: {self.conn.sentence_id}"
                )

                if message.sentence_type == SentenceType.FIRST:
                    self.conn.client_abort = False

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
                                f"Auto-generated new session ID: {self.conn.sentence_id}"
                            )

                        # AliyunStream-specific parameter generation
                        self.message_id = str(uuid.uuid4().hex)

                        logger.bind(tag=TAG).info("Starting TTS session...")
                        future = asyncio.run_coroutine_threadsafe(
                            self.start_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                        future.result()
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
                    if message.content_file and os.path.exists(message.content_file):
                        # Process file audio data first
                        file_audio = self._process_audio_file(
                            message.content_file)
                        self.before_stop_play_files.append(
                            (file_audio, message.content_detail)
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
                    f"Failed to process TTS text: {str(e)}, Type: {type(e).__name__}, Stack: {traceback.format_exc()}"
                )

    async def text_to_speak(self, text, _):
        try:
            if self.ws is None:
                logger.bind(tag=TAG).warning(
                    f"WebSocket connection does not exist, terminating text sending")
                return
            filtered_text = MarkdownCleaner.clean_markdown(text)
            run_request = {
                "header": {
                    "message_id": self.message_id,
                    "task_id": self.conn.sentence_id,
                    "namespace": "FlowingSpeechSynthesizer",
                    "name": "RunSynthesis",
                    "appkey": self.appkey,
                },
                "payload": {"text": filtered_text},
            }
            await self.ws.send(json.dumps(run_request))
            self.last_active_time = time.time()
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
        logger.bind(tag=TAG).info(f"Starting session～～{session_id}")
        try:
            # Check previous session monitoring status when session starts
            if (
                self._monitor_task is not None
                and isinstance(self._monitor_task, Task)
                and not self._monitor_task.done()
            ):
                logger.bind(tag=TAG).info(
                    "Detected incomplete previous session, closing monitoring task and connection..."
                )
                await self.close()

            # Establish new connection
            await self._ensure_connection()

            # Start monitoring task
            self._monitor_task = asyncio.create_task(
                self._start_monitor_tts_response())

            start_request = {
                "header": {
                    "message_id": self.message_id,
                    "task_id": self.conn.sentence_id,
                    "namespace": "FlowingSpeechSynthesizer",
                    "name": "StartSynthesis",
                    "appkey": self.appkey,
                },
                "payload": {
                    "voice": self.voice,
                    "format": self.format,
                    "sample_rate": self.sample_rate,
                    "volume": self.volume,
                    "speech_rate": self.speech_rate,
                    "pitch_rate": self.pitch_rate,
                    "enable_subtitle": True,
                },
            }
            await self.ws.send(json.dumps(start_request))
            self.last_active_time = time.time()
            logger.bind(tag=TAG).info("Session start request sent")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to start session: {str(e)}")
            # 确保清理资源
            await self.close()
            raise

    async def finish_session(self, session_id):
        logger.bind(tag=TAG).info(f"Closing session～～{session_id}")
        try:
            if self.ws:
                stop_request = {
                    "header": {
                        "message_id": self.message_id,
                        "task_id": self.conn.sentence_id,
                        "namespace": "FlowingSpeechSynthesizer",
                        "name": "StopSynthesis",
                        "appkey": self.appkey,
                    }
                }
                await self.ws.send(json.dumps(stop_request))
                logger.bind(tag=TAG).info("Session end request sent")
                self.last_active_time = time.time()
                if self._monitor_task:
                    try:
                        await self._monitor_task
                    except Exception as e:
                        logger.bind(tag=TAG).error(
                            f"Error occurred while waiting for monitoring task to complete: {str(e)}"
                        )
                    finally:
                        self._monitor_task = None
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to close session: {str(e)}")
            # 确保清理资源
            await self.close()
            raise

    async def close(self):
        """Resource cleanup"""
        if self._monitor_task:
            try:
                self._monitor_task.cancel()
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.bind(tag=TAG).warning(
                    f"Error canceling monitoring task during close: {e}")
            self._monitor_task = None

        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None
            self.last_active_time = None

    async def _start_monitor_tts_response(self):
        """Monitor TTS responses"""
        opus_datas_cache = []
        is_first_sentence = True
        first_sentence_segment_count = 0  # Add counter
        try:
            session_finished = False  # Mark whether session ended normally
            while not self.conn.stop_event.is_set():
                try:
                    msg = await self.ws.recv()
                    self.last_active_time = time.time()
                    # Check if client aborted
                    if self.conn.client_abort:
                        logger.bind(tag=TAG).info(
                            "Received interruption signal, terminating TTS response monitoring")
                        break
                    if isinstance(msg, str):  # Text control message
                        try:
                            data = json.loads(msg)
                            header = data.get("header", {})
                            event_name = header.get("name")
                            if event_name == "SynthesisStarted":
                                logger.bind(tag=TAG).debug(
                                    "TTS synthesis started")
                                self.tts_audio_queue.put(
                                    (SentenceType.FIRST, [], None)
                                )
                            elif event_name == "SentenceBegin":
                                opus_datas_cache = []
                            elif event_name == "SentenceEnd":
                                if (
                                    not is_first_sentence
                                    or first_sentence_segment_count > 10
                                ):
                                    # Send cached data
                                    if self.conn.tts_MessageText:
                                        logger.bind(tag=TAG).info(
                                            f"Sentence voice generation successful: {self.conn.tts_MessageText}"
                                        )
                                        self.tts_audio_queue.put(
                                            (SentenceType.MIDDLE, opus_datas_cache,
                                             self.conn.tts_MessageText)
                                        )
                                        self.conn.tts_MessageText = None
                                    else:
                                        self.tts_audio_queue.put(
                                            (SentenceType.MIDDLE,
                                             opus_datas_cache, None)
                                        )
                                # After first sentence ends, set flag to False
                                is_first_sentence = False
                            elif event_name == "SynthesisCompleted":
                                logger.bind(tag=TAG).debug(f"Session ended～～")
                                self._process_before_stop_play_files()
                                session_finished = True
                                break
                        except json.JSONDecodeError:
                            logger.bind(tag=TAG).warning(
                                "Received invalid JSON message")
                    # Binary message (audio data)
                    elif isinstance(msg, (bytes, bytearray)):
                        logger.bind(tag=TAG).debug(f"Pushing data to queue～～")
                        opus_datas = self.opus_encoder.encode_pcm_to_opus(
                            msg, False)
                        logger.bind(tag=TAG).debug(
                            f"Pushing data to queue frame count～～{len(opus_datas)}"
                        )
                        if is_first_sentence:
                            first_sentence_segment_count += 1
                            if first_sentence_segment_count <= 6:
                                self.tts_audio_queue.put(
                                    (SentenceType.MIDDLE, opus_datas, None)
                                )
                            else:
                                opus_datas_cache.extend(opus_datas)
                        else:
                            # Cache subsequent sentences
                            opus_datas_cache.extend(opus_datas)

                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).warning("WebSocket connection closed")
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"Error processing TTS response: {e}\n{traceback.format_exc()}"
                    )
                    break
            # Only close on connection exception
            if not session_finished and self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
        # Clean up references when monitoring task exits
        finally:
            self._monitor_task = None

    def to_tts(self, text: str) -> list:
        """Non-streaming TTS processing, used for testing and saving audio files scenarios"""
        try:
            # Create new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Generate session ID
            session_id = uuid.uuid4().hex
            # Store audio data
            audio_data = []

            async def _generate_audio():
                # Refresh Token (if needed)
                if self._is_token_expired():
                    self._refresh_token()

                # Establish WebSocket connection
                ws = await websockets.connect(
                    self.ws_url,
                    additional_headers={"X-NLS-Token": self.token},
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10,
                )
                try:
                    # Send StartSynthesis request
                    start_message_id = str(uuid.uuid4().hex)
                    start_request = {
                        "header": {
                            "message_id": start_message_id,
                            "task_id": session_id,
                            "namespace": "FlowingSpeechSynthesizer",
                            "name": "StartSynthesis",
                            "appkey": self.appkey,
                        },
                        "payload": {
                            "voice": self.voice,
                            "format": self.format,
                            "sample_rate": self.sample_rate,
                            "volume": self.volume,
                            "speech_rate": self.speech_rate,
                            "pitch_rate": self.pitch_rate,
                            "enable_subtitle": True,
                        },
                    }
                    await ws.send(json.dumps(start_request))

                    # Wait for SynthesisStarted response
                    synthesis_started = False
                    while not synthesis_started:
                        msg = await ws.recv()
                        if isinstance(msg, str):
                            data = json.loads(msg)
                            header = data.get("header", {})
                            if header.get("name") == "SynthesisStarted":
                                synthesis_started = True
                                logger.bind(tag=TAG).debug(
                                    "TTS synthesis started")
                            elif header.get("name") == "TaskFailed":
                                error_info = data.get("payload", {}).get(
                                    "error_info", {}
                                )
                                error_code = error_info.get("error_code")
                                error_message = error_info.get(
                                    "error_message", "未知错误"
                                )
                                raise Exception(
                                    f"Failed to start synthesis: {error_code} - {error_message}"
                                )

                    # Send text synthesis request
                    filtered_text = MarkdownCleaner.clean_markdown(text)
                    run_message_id = str(uuid.uuid4().hex)
                    run_request = {
                        "header": {
                            "message_id": run_message_id,
                            "task_id": session_id,
                            "namespace": "FlowingSpeechSynthesizer",
                            "name": "RunSynthesis",
                            "appkey": self.appkey,
                        },
                        "payload": {"text": filtered_text},
                    }
                    await ws.send(json.dumps(run_request))

                    # Send stop synthesis request
                    stop_message_id = str(uuid.uuid4().hex)
                    stop_request = {
                        "header": {
                            "message_id": stop_message_id,
                            "task_id": session_id,
                            "namespace": "FlowingSpeechSynthesizer",
                            "name": "StopSynthesis",
                            "appkey": self.appkey,
                        }
                    }
                    await ws.send(json.dumps(stop_request))

                    # Receive audio data
                    synthesis_completed = False
                    while not synthesis_completed:
                        msg = await ws.recv()
                        if isinstance(msg, (bytes, bytearray)):
                            # Encode to Opus and collect
                            opus_frames = self.opus_encoder.encode_pcm_to_opus(
                                msg, False
                            )
                            audio_data.extend(opus_frames)
                        elif isinstance(msg, str):
                            data = json.loads(msg)
                            header = data.get("header", {})
                            event_name = header.get("name")
                            if event_name == "SynthesisCompleted":
                                synthesis_completed = True
                                logger.bind(tag=TAG).debug(
                                    "TTS synthesis completed")
                            elif event_name == "TaskFailed":
                                error_info = data.get("payload", {}).get(
                                    "error_info", {}
                                )
                                error_code = error_info.get("error_code")
                                error_message = error_info.get(
                                    "error_message", "未知错误"
                                )
                                raise Exception(
                                    f"Synthesis failed: {error_code} - {error_message}"
                                )
                finally:
                    try:
                        await ws.close()
                    except:
                        pass

            loop.run_until_complete(_generate_audio())
            loop.close()

            return audio_data
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Failed to generate audio data: {str(e)}")
            return []
