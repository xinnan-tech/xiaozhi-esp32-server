import json
import time
import uuid
import hmac
import base64
import hashlib
import asyncio
import requests
import websockets
import opuslib_next
import random
from typing import Optional, Tuple, List
from urllib import parse
from datetime import datetime
from config.logger import setup_logging
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

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
            "RegionId": "cn-shanghai",
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid1()),
            "SignatureVersion": "1.0",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "Version": "2019-02-28",
        }
        query_string = AccessToken._encode_dict(parameters)
        string_to_sign = (
            "GET" + "&" +
            AccessToken._encode_text("/") + "&" +
            AccessToken._encode_text(query_string)
        )
        secreted_string = hmac.new(
            bytes(access_key_secret + "&", encoding="utf-8"),
            bytes(string_to_sign, encoding="utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(secreted_string)
        signature = AccessToken._encode_text(signature)
        full_url = "http://nls-meta.cn-shanghai.aliyuncs.com/?Signature=%s&%s" % (
            signature, query_string)
        response = requests.get(full_url)
        if response.ok:
            root_obj = response.json()
            if "Token" in root_obj:
                return root_obj["Token"]["Id"], root_obj["Token"]["ExpireTime"]
        return None, None


class ASRProvider(ASRProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.text = ""
        self.decoder = opuslib_next.Decoder(16000, 1)
        self.asr_ws = None
        self.forward_task = None
        self.is_processing = False
        self.server_ready = False  # Server ready status

        # Basic configuration
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")
        self.appkey = config.get("appkey")
        self.token = config.get("token")
        self.host = config.get("host", "nls-gateway-cn-shanghai.aliyuncs.com")
        # If configured with internal address (contains -internal.aliyuncs.com), use ws protocol, default is wss protocol
        if "-internal." in self.host:
            self.ws_url = f"ws://{self.host}/ws/v1"
        else:
            # Default to wss protocol
            self.ws_url = f"wss://{self.host}/ws/v1"

        self.max_sentence_silence = config.get("max_sentence_silence")
        self.output_dir = config.get("output_dir", "./audio_output")
        self.delete_audio_file = delete_audio_file
        self.expire_time = None

        # Token management
        if self.access_key_id and self.access_key_secret:
            self._refresh_token()
        elif not self.token:
            raise ValueError(
                "Must provide access_key_id+access_key_secret or provide token directly")

    def _refresh_token(self):
        """Refresh Token"""
        self.token, expire_time_str = AccessToken.create_token(
            self.access_key_id, self.access_key_secret)
        if not self.token:
            raise ValueError("Unable to obtain valid access Token")

        try:
            expire_str = str(expire_time_str).strip()
            if expire_str.isdigit():
                expire_time = datetime.fromtimestamp(int(expire_str))
            else:
                expire_time = datetime.strptime(
                    expire_str, "%Y-%m-%dT%H:%M:%SZ")
            self.expire_time = expire_time.timestamp() - 60
        except:
            self.expire_time = None

    def _is_token_expired(self):
        """Check if Token is expired"""
        return self.expire_time and time.time() > self.expire_time

    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)

    async def receive_audio(self, conn, audio, audio_have_voice):
        # Initialize audio cache
        if not hasattr(conn, 'asr_audio_for_voiceprint'):
            conn.asr_audio_for_voiceprint = []

        # Store audio data
        if audio:
            conn.asr_audio_for_voiceprint.append(audio)

        conn.asr_audio.append(audio)
        conn.asr_audio = conn.asr_audio[-10:]

        # Only establish connection when there is voice and no existing connection
        if audio_have_voice and not self.is_processing:
            try:
                await self._start_recognition(conn)
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Failed to start recognition: {str(e)}")
                await self._cleanup(conn)
                return

        if self.asr_ws and self.is_processing and self.server_ready:
            try:
                pcm_frame = self.decoder.decode(audio, 960)
                await self.asr_ws.send(pcm_frame)
            except Exception as e:
                logger.bind(tag=TAG).warning(f"Failed to send audio: {str(e)}")
                await self._cleanup(conn)

    async def _start_recognition(self, conn):
        """Start recognition session"""
        if self._is_token_expired():
            self._refresh_token()

        # Establish connection
        headers = {"X-NLS-Token": self.token}
        self.asr_ws = await websockets.connect(
            self.ws_url,
            additional_headers=headers,
            max_size=1000000000,
            ping_interval=None,
            ping_timeout=None,
            close_timeout=5,
        )

        self.is_processing = True
        self.server_ready = False  # Reset server ready status
        self.forward_task = asyncio.create_task(self._forward_results(conn))

        # Send start request
        start_request = {
            "header": {
                "namespace": "SpeechTranscriber",
                "name": "StartTranscription",
                "status": 20000000,
                "message_id": ''.join(random.choices('0123456789abcdef', k=32)),
                "task_id": ''.join(random.choices('0123456789abcdef', k=32)),
                "status_text": "Gateway:SUCCESS:Success.",
                "appkey": self.appkey
            },
            "payload": {
                "format": "pcm",
                "sample_rate": 16000,
                "enable_intermediate_result": True,
                "enable_punctuation_prediction": True,
                "enable_inverse_text_normalization": True,
                "max_sentence_silence": self.max_sentence_silence,
                "enable_voice_detection": False,
            }
        }
        await self.asr_ws.send(json.dumps(start_request, ensure_ascii=False))
        logger.bind(tag=TAG).info(
            "Start request sent, waiting for server to be ready...")

    async def _forward_results(self, conn):
        """Forward recognition results"""
        try:
            while self.asr_ws and not conn.stop_event.is_set():
                try:
                    response = await asyncio.wait_for(self.asr_ws.recv(), timeout=1.0)
                    result = json.loads(response)

                    header = result.get("header", {})
                    payload = result.get("payload", {})
                    message_name = header.get("name", "")
                    status = header.get("status", 0)

                    if status != 20000000:
                        # Connection timeout or client disconnect
                        if status in [40000004, 40010004]:
                            logger.bind(tag=TAG).warning(
                                f"Connection issue, status code: {status}")
                            break
                        elif status in [40270002, 40270003]:  # Audio issues
                            logger.bind(tag=TAG).warning(
                                f"Audio processing issue, status code: {status}")
                            continue
                        else:
                            logger.bind(tag=TAG).error(
                                f"Recognition error, status code: {status}, message: {header.get('status_text', '')}")
                            continue

                    # TranscriptionStarted indicates server is ready to receive audio data
                    if message_name == "TranscriptionStarted":
                        self.server_ready = True
                        logger.bind(tag=TAG).info(
                            "Server is ready, starting to send cached audio...")

                        # Send cached audio
                        if conn.asr_audio:
                            for cached_audio in conn.asr_audio[-10:]:
                                try:
                                    pcm_frame = self.decoder.decode(
                                        cached_audio, 960)
                                    await self.asr_ws.send(pcm_frame)
                                except Exception as e:
                                    logger.bind(tag=TAG).warning(
                                        f"Failed to send cached audio: {e}")
                                    break
                        continue

                    if message_name == "TranscriptionResultChanged":
                        # Intermediate result
                        text = payload.get("result", "")
                        if text:
                            self.text = text
                    elif message_name == "SentenceEnd":
                        # Final result
                        text = payload.get("result", "")
                        if text:
                            self.text = text
                            conn.reset_vad_states()
                            # Pass cached audio data
                            audio_data = getattr(
                                conn, 'asr_audio_for_voiceprint', [])
                            await self.handle_voice_stop(conn, audio_data)
                            # Clear cache
                            conn.asr_audio_for_voiceprint = []
                            break
                    elif message_name == "TranscriptionCompleted":
                        # Recognition completed
                        self.is_processing = False
                        break

                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"Failed to process result: {str(e)}")
                    break

        except Exception as e:
            logger.bind(tag=TAG).error(f"Result forwarding failed: {str(e)}")
        finally:
            await self._cleanup(conn)

    async def _cleanup(self, conn):
        """Clean up resources"""
        logger.bind(tag=TAG).info(
            f"Starting ASR session cleanup | Current status: processing={self.is_processing}, server_ready={self.server_ready}")

        # Clean up connection's audio cache
        if conn and hasattr(conn, 'asr_audio_for_voiceprint'):
            conn.asr_audio_for_voiceprint = []

        # Determine if stop request needs to be sent
        should_stop = self.is_processing or self.server_ready

        # Send stop recognition request
        if self.asr_ws and should_stop:
            try:
                stop_msg = {
                    "header": {
                        "namespace": "SpeechTranscriber",
                        "name": "StopTranscription",
                        "status": 20000000,
                        "message_id": ''.join(random.choices('0123456789abcdef', k=32)),
                        "status_text": "Client:Stop",
                        "appkey": self.appkey
                    }
                }
                logger.bind(tag=TAG).info("Sending ASR termination request")
                await self.asr_ws.send(json.dumps(stop_msg, ensure_ascii=False))
                await asyncio.sleep(0.1)
                logger.bind(tag=TAG).info("ASR termination request sent")
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"ASR termination request failed to send: {e}")

        # Status reset (after termination request is sent)
        self.is_processing = False
        self.server_ready = False
        logger.bind(tag=TAG).info("ASR status has been reset")

        # Clean up tasks
        if self.forward_task and not self.forward_task.done():
            self.forward_task.cancel()
            try:
                await asyncio.wait_for(self.forward_task, timeout=1.0)
            except Exception as e:
                logger.bind(tag=TAG).debug(
                    f"forward_task cancellation exception: {e}")
            finally:
                self.forward_task = None

        # Close connection
        if self.asr_ws:
            try:
                logger.bind(tag=TAG).debug("Closing WebSocket connection")
                await asyncio.wait_for(self.asr_ws.close(), timeout=2.0)
                logger.bind(tag=TAG).debug("WebSocket connection closed")
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Failed to close WebSocket connection: {e}")
            finally:
                self.asr_ws = None

        logger.bind(tag=TAG).info("ASR session cleanup completed")

    async def speech_to_text(self, opus_data, session_id, audio_format):
        """Get recognition result"""
        result = self.text
        self.text = ""
        return result, None

    async def close(self):
        """Close resources"""
        await self._cleanup()
