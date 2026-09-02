import os
import time
import uuid
import json
import hmac
import queue
import base64
import hashlib
import asyncio
import traceback
import websockets
from asyncio import Task
from config.logger import setup_logging
from core.utils import opus_encoder_utils
from core.utils.tts import MarkdownCleaner
from urllib.parse import urlencode, urlparse
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType

TAG = __name__
logger = setup_logging()


class XunfeiWSAuth:
    @staticmethod
    def create_auth_url(api_key, api_secret, api_url):
        """Generate Xunfei WebSocket Auth URL"""
        parsed_url = urlparse(api_url)
        host = parsed_url.netloc
        path = parsed_url.path

        # Get UTC time, Xunfei requires RFC1123 format
        now = time.gmtime()
        date = time.strftime('%a, %d %b %Y %H:%M:%S GMT', now)

        # Construct signature string
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"

        # Calculate signature
        signature_sha = hmac.new(
            api_secret.encode('utf-8'),
            signature_origin.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding='utf-8')

        # Construct authorization
        authorization_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')

        # Construct final WebSocket URL
        v = {
            "authorization": authorization,
            "date": date,
            "host": host
        }
        url = api_url + '?' + urlencode(v)
        return url


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)

        # Set to stream interface type
        self.interface_type = InterfaceType.DUAL_STREAM

        # Basic config
        self.app_id = config.get("app_id")
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")

        # Interface address
        self.api_url = config.get("api_url", "wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6")

        # Voice config
        self.voice = config.get("voice", "x5_lingxiaoxuan_flow")
        if config.get("private_voice"):
            self.voice = config.get("private_voice")

        # Audio parameter config
        speed = config.get("speed", "50")
        self.speed = int(speed) if speed else 50

        volume = config.get("volume", "50")
        self.volume = int(volume) if volume else 50

        pitch = config.get("pitch", "50")
        self.pitch = int(pitch) if pitch else 50

        # Audio encoding config
        self.format = config.get("format", "raw")

        sample_rate = config.get("sample_rate", "24000")
        self.sample_rate = int(sample_rate) if sample_rate else 24000

        # Colloquial config
        self.oral_level = config.get("oral_level", "mid")

        spark_assist = config.get("spark_assist", "1")
        self.spark_assist = int(spark_assist) if spark_assist else 1

        stop_split = config.get("stop_split", "0")
        self.stop_split = int(stop_split) if stop_split else 0
    
        remain = config.get("remain", "0")
        self.remain = int(remain) if remain else 0

        # WebSocket config
        self.ws = None
        self._monitor_task = None

        # Sequence number management
        self.text_seq = 0

        # Create Opus encoder
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=self.sample_rate, channels=1, frame_size_ms=60
        )

        # Verify required parameters
        if not all([self.app_id, self.api_key, self.api_secret]):
            raise ValueError("Xunfei TTS requires app_id, api_key and api_secret")

    async def _ensure_connection(self):
        """Ensure WebSocket connection is available"""
        try:
            logger.bind(tag=TAG).info("Starting to establish new connection...")

            # Generate Auth URL
            auth_url = XunfeiWSAuth.create_auth_url(
                self.api_key, self.api_secret, self.api_url
            )

            self.ws = await websockets.connect(
                auth_url,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10,
            )
            logger.bind(tag=TAG).info("WebSocket connection established successfully")
            return self.ws
        except Exception as e:
            logger.bind(tag=TAG).error(f"Connection failed: {str(e)}")
            self.ws = None
            raise

    def tts_text_priority_thread(self):
        """Streaming text processing thread"""
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                logger.bind(tag=TAG).debug(
                    f"Received TTS task | {message.sentence_type.name} | {message.content_type.name} | Session ID: {self.conn.sentence_id}"
                )

                if message.sentence_type == SentenceType.FIRST:
                    # Reset sequence number
                    self.text_seq = 0
                    self.conn.client_abort = False
                # Increment sequence number
                self.text_seq += 1
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("Received interrupt info, terminating TTS text processing thread")
                    continue

                if message.sentence_type == SentenceType.FIRST:
                    # Initialize parameters
                    try:
                        if not getattr(self.conn, "sentence_id", None):
                            self.conn.sentence_id = uuid.uuid4().hex
                            logger.bind(tag=TAG).info(f"Automatically generated new Session ID: {self.conn.sentence_id}")

                        logger.bind(tag=TAG).info("Starting TTS session...")
                        future = asyncio.run_coroutine_threadsafe(
                            self.start_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                        future.result()
                        self.before_stop_play_files.clear()
                        logger.bind(tag=TAG).info("TTS session started successfully")

                    except Exception as e:
                        logger.bind(tag=TAG).error(f"Failed to start TTS session: {str(e)}")
                        continue

                # Process text content
                if ContentType.TEXT == message.content_type:
                    if message.content_detail:
                        try:
                            logger.bind(tag=TAG).debug(
                                f"Starting to send TTS text: {message.content_detail}"
                            )
                            future = asyncio.run_coroutine_threadsafe(
                                self.text_to_speak(message.content_detail, None),
                                loop=self.conn.loop,
                            )
                            future.result()
                            logger.bind(tag=TAG).debug("TTS text sent successfully")
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"Failed to send TTS text: {str(e)}")
                            # Do not use continue, ensure subsequent processing is not interrupted

                # Process file content
                if ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(
                        f"Adding audio file to playlist: {message.content_file}"
                    )
                    if message.content_file and os.path.exists(message.content_file):
                        # Process file audio data first
                        self._process_audio_file_stream(message.content_file, callback=lambda audio_data: self.handle_audio_file(audio_data, message.content_detail))

                # Process session end
                if message.sentence_type == SentenceType.LAST:
                    try:
                        logger.bind(tag=TAG).info("Starting to end TTS session...")
                        asyncio.run_coroutine_threadsafe(
                            self.finish_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"Failed to end TTS session: {str(e)}")
                        continue

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Failed to process TTS text: {str(e)}, Type: {type(e).__name__}, Stack: {traceback.format_exc()}"
                )

    async def text_to_speak(self, text, _):
        """Send text to TTS service for synthesis"""
        try:
            if self.ws is None:
                logger.bind(tag=TAG).warning(f"WebSocket connection does not exist, stop sending text")
                return

            filtered_text = MarkdownCleaner.clean_markdown(text)
            if filtered_text:
                # Send text synthesis request
                run_request = self._build_base_request(status=1,text=filtered_text)
                await self.ws.send(json.dumps(run_request))
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
        logger.bind(tag=TAG).info(f"Starting session~~{session_id}")
        try:
            # Check listening status of previous session when session starts
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
            self._monitor_task = asyncio.create_task(self._start_monitor_tts_response())

            # Send session start request
            start_request = self._build_base_request(status=0)

            await self.ws.send(json.dumps(start_request))
            logger.bind(tag=TAG).info("Session start request sent")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to start session: {str(e)}")
            # Ensure resources are cleaned up
            await self.close()
            raise

    async def finish_session(self, session_id):
        logger.bind(tag=TAG).info(f"Closing session~~{session_id}")
        try:
            if self.ws:
                # Send session end request
                stop_request = self._build_base_request(status=2)
                await self.ws.send(json.dumps(stop_request))
                logger.bind(tag=TAG).info("Session end request sent")

                if self._monitor_task:
                    try:
                        await self._monitor_task
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"Error waiting for monitoring task to complete: {str(e)}")
                    finally:
                        self._monitor_task = None
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to close session: {str(e)}")
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
                logger.bind(tag=TAG).warning(f"Error cancelling monitoring task during close: {e}")
            self._monitor_task = None

        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None

    async def _start_monitor_tts_response(self):
        """Monitor TTS response"""
        try:
            while not self.conn.stop_event.is_set():
                try:
                    msg = await self.ws.recv()

                    # Check if client aborted
                    if self.conn.client_abort:
                        logger.bind(tag=TAG).info("Received interrupt info, stop monitoring TTS response")
                        break

                    try:
                        data = json.loads(msg)
                        header = data.get("header", {})
                        code = header.get("code")

                        if code == 0:
                            payload = data.get("payload", {})
                            audio_payload = payload.get("audio", {})

                            if audio_payload:
                                status = audio_payload.get("status", 0)
                                audio_data = audio_payload.get("audio", "")
                                if status == 0:
                                    logger.bind(tag=TAG).debug("TTS synthesis started")
                                    self.tts_audio_queue.put(
                                        (SentenceType.FIRST, [], None)
                                    )
                                elif status == 2:
                                    logger.bind(tag=TAG).debug("Received end status audio data, TTS synthesis completed")
                                    self._process_before_stop_play_files()
                                    break
                                else:
                                    if self.conn.tts_MessageText:
                                        logger.bind(tag=TAG).info(
                                            f"Sentence voice generation successful: {self.conn.tts_MessageText}"
                                        )
                                        self.tts_audio_queue.put(
                                            (SentenceType.FIRST, [], self.conn.tts_MessageText)
                                        )
                                        self.conn.tts_MessageText = None
                                    try:
                                        audio_bytes = base64.b64decode(audio_data)
                                        self.opus_encoder.encode_pcm_to_opus_stream(
                                            audio_bytes, False, self.handle_opus
                                        )

                                    except Exception as e:
                                        logger.bind(tag=TAG).error(f"Failed to process audio data: {e}")

                        else:
                            message = header.get("message", "Unknown error")
                            logger.bind(tag=TAG).error(f"TTS synthesis error: {code} - {message}")
                            break

                    except json.JSONDecodeError:
                        logger.bind(tag=TAG).warning("Received invalid JSON message")

                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).warning("WebSocket connection closed")
                    break

                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"Error processing TTS response: {e}\n{traceback.format_exc()}"
                    )
                    break

            # Connection not reusable
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
        # Clean up reference when monitoring task exits
        finally:
            self._monitor_task = None

    def to_tts(self, text: str) -> list:
        """Non-streaming TTS processing, used for testing and saving audio files"""
        try:
            # Create new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Store audio data
            audio_data = []

            async def _generate_audio():
                # Generate Auth URL
                auth_url = XunfeiWSAuth.create_auth_url(
                    self.api_key, self.api_secret, self.api_url
                )

                # Establish WebSocket connection
                ws = await websockets.connect(
                    auth_url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10,
                )

                try:
                    filtered_text = MarkdownCleaner.clean_markdown(text)

                    text_request = self._build_base_request(status=2,text=filtered_text)

                    await ws.send(json.dumps(text_request))

                    task_finished = False
                    while not task_finished:
                        msg = await ws.recv()

                        data = json.loads(msg)
                        header = data.get("header", {})
                        code = header.get("code")

                        if code == 0:
                            payload = data.get("payload", {})
                            audio_payload = payload.get("audio", {})
                            if audio_payload:
                                status = audio_payload.get("status", 0)
                                audio_base64 = audio_payload.get("audio", "")
                                if status == 1:
                                    try:
                                        audio_bytes = base64.b64decode(audio_base64)
                                        self.opus_encoder.encode_pcm_to_opus_stream(
                                            audio_bytes,
                                            end_of_stream=False,
                                            callback=lambda opus: audio_data.append(opus)
                                        )
                                    except Exception as e:
                                        logger.bind(tag=TAG).error(f"Failed to process audio data: {e}")
                                elif status == 2:
                                    task_finished = True
                                    logger.bind(tag=TAG).debug("TTS task completed")

                        else:
                            message = header.get("message", "Unknown error")
                            raise Exception(f"Synthesis failed: {code} - {message}")

                finally:
                    # Clean up resources
                    try:
                        await ws.close()
                    except:
                        pass

            loop.run_until_complete(_generate_audio())
            loop.close()

            return audio_data
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to generate audio data: {str(e)}")
            return []        
    
    def _build_base_request(self, status,text=" "):
        """Build base request structure"""
        return {
            "header": {
                "app_id": self.app_id,
                "status": status,
            },
            "parameter": {
                "oral": {
                    "oral_level": self.oral_level,
                    "spark_assist": self.spark_assist,
                    "stop_split": self.stop_split,
                    "remain": self.remain
                },
                "tts": {
                    "vcn": self.voice,
                    "speed": self.speed,
                    "volume": self.volume,
                    "pitch": self.pitch,
                    "bgs": 0,
                    "reg": 0,
                    "rdn": 0,
                    "rhy": 0,
                    "audio": {
                        "encoding": self.format,
                        "sample_rate": self.sample_rate,
                        "channels": 1,
                        "bit_depth": 16,
                        "frame_size": 0
                    }
                }
            },
            "payload": {
                "text": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "plain",
                    "status": status,
                    "seq": self.text_seq,
                    "text": base64.b64encode(text.encode('utf-8')).decode('utf-8')
                }
            }
        }
