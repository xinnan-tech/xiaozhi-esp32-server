import json
import gzip
import uuid
import asyncio
import websockets
import opuslib_next
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.text = ""
        self.decoder = opuslib_next.Decoder(16000, 1)
        self.asr_ws = None
        self.forward_task = None
        self.is_processing = False  # Add processing status flag

        # Configuration parameters
        self.appid = str(config.get("appid"))
        self.cluster = config.get("cluster")
        self.access_token = config.get("access_token")
        self.boosting_table_name = config.get("boosting_table_name", "")
        self.correct_table_name = config.get("correct_table_name", "")
        self.output_dir = config.get("output_dir", "tmp/")
        self.delete_audio_file = delete_audio_file

        # Volcengine ASR configuration
        enable_multilingual = config.get("enable_multilingual", False)
        self.enable_multilingual = False if str(enable_multilingual).lower() == 'false' else True
        if self.enable_multilingual:
            self.ws_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream"
        else:
            self.ws_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
        self.uid = config.get("uid", "streaming_asr_service")
        self.workflow = config.get(
            "workflow", "audio_in,resample,partition,vad,fe,decode,itn,nlu_punctuate"
        )
        self.result_type = config.get("result_type", "single")
        self.format = config.get("format", "pcm")
        self.codec = config.get("codec", "pcm")
        self.rate = config.get("sample_rate", 16000)
        # language parameter is only valid in multilingual mode (bigmodel_nostream)
        self.language = config.get("language") if self.enable_multilingual else None
        self.bits = config.get("bits", 16)
        self.channel = config.get("channel", 1)
        self.auth_method = config.get("auth_method", "token")
        self.secret = config.get("secret", "access_secret")
        end_window_size = config.get("end_window_size")
        self.end_window_size = int(end_window_size) if end_window_size else 200

    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)

    async def receive_audio(self, conn, audio, audio_have_voice):
        conn.asr_audio.append(audio)
        conn.asr_audio = conn.asr_audio[-10:]
        # Store audio data
        if not hasattr(conn, 'asr_audio_for_voiceprint'):
            conn.asr_audio_for_voiceprint = []
        conn.asr_audio_for_voiceprint.append(audio)

        # Process complete voice segment when no audio data
        if conn.client_listen_mode != "manual" and not audio and len(conn.asr_audio_for_voiceprint) > 0:
            await self.handle_voice_stop(conn, conn.asr_audio_for_voiceprint)
            conn.asr_audio_for_voiceprint = []

        # If voice detected, and connection not established
        if audio_have_voice and self.asr_ws is None and not self.is_processing:
            try:
                self.is_processing = True
                # Establish new WebSocket connection
                headers = self.token_auth() if self.auth_method == "token" else None
                logger.bind(tag=TAG).info(f"Connecting to ASR service, headers: {headers}")

                self.asr_ws = await websockets.connect(
                    self.ws_url,
                    additional_headers=headers,
                    max_size=1000000000,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=10,
                )

                # Send initialization request
                request_params = self.construct_request(str(uuid.uuid4()))
                try:
                    payload_bytes = str.encode(json.dumps(request_params))
                    payload_bytes = gzip.compress(payload_bytes)
                    full_client_request = self.generate_header()
                    full_client_request.extend((len(payload_bytes)).to_bytes(4, "big"))
                    full_client_request.extend(payload_bytes)

                    logger.bind(tag=TAG).info(f"Send initialization request: {request_params}")
                    await self.asr_ws.send(full_client_request)

                    # Wait for initialization response
                    init_res = await self.asr_ws.recv()
                    result = self.parse_response(init_res)
                    logger.bind(tag=TAG).info(f"Received initialization response: {result}")

                    # Check initialization response
                    if "code" in result and result["code"] != 1000:
                        error_msg = f"ASR service initialization failed: {result.get('payload_msg', {}).get('error', 'Unknown error')}"
                        logger.bind(tag=TAG).error(error_msg)
                        raise Exception(error_msg)

                except Exception as e:
                    logger.bind(tag=TAG).error(f"Failed to send initialization request: {str(e)}")
                    if hasattr(e, "__cause__") and e.__cause__:
                        logger.bind(tag=TAG).error(f"Error cause: {str(e.__cause__)}")
                    raise e

                # Start async task to receive ASR results
                self.forward_task = asyncio.create_task(self._forward_asr_results(conn))

                # Send cached audio data
                if conn.asr_audio and len(conn.asr_audio) > 0:
                    for cached_audio in conn.asr_audio[-10:]:
                        try:
                            pcm_frame = self.decoder.decode(cached_audio, 960)
                            payload = gzip.compress(pcm_frame)
                            audio_request = bytearray(
                                self.generate_audio_default_header()
                            )
                            audio_request.extend(len(payload).to_bytes(4, "big"))
                            audio_request.extend(payload)
                            await self.asr_ws.send(audio_request)
                        except Exception as e:
                            logger.bind(tag=TAG).info(
                                f"Error sending cached audio data: {e}"
                            )

            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to establish ASR connection: {str(e)}")
                if hasattr(e, "__cause__") and e.__cause__:
                    logger.bind(tag=TAG).error(f"Error cause: {str(e.__cause__)}")
                if self.asr_ws:
                    await self.asr_ws.close()
                    self.asr_ws = None
                self.is_processing = False
                return

        # Send current audio data
        if self.asr_ws and self.is_processing:
            try:
                pcm_frame = self.decoder.decode(audio, 960)
                payload = gzip.compress(pcm_frame)
                audio_request = bytearray(self.generate_audio_default_header())
                audio_request.extend(len(payload).to_bytes(4, "big"))
                audio_request.extend(payload)
                await self.asr_ws.send(audio_request)
            except Exception as e:
                logger.bind(tag=TAG).info(f"Error sending audio data: {e}")

    async def _forward_asr_results(self, conn):
        try:
            while self.asr_ws and not conn.stop_event.is_set():
                # Get audio data of current connection
                audio_data = getattr(conn, 'asr_audio_for_voiceprint', [])
                try:
                    response = await self.asr_ws.recv()
                    result = self.parse_response(response)
                    logger.bind(tag=TAG).debug(f"Received ASR result: {result}")

                    if "payload_msg" in result:
                        payload = result["payload_msg"]
                        # Check if it is error code 1013 (no valid voice)
                        if "code" in payload and payload["code"] == 1013:
                            # Silent handling, do not log error
                            continue

                        if "result" in payload:
                            utterances = payload["result"].get("utterances", [])
                            # Check duration and empty text cases
                            if (
                                not self.enable_multilingual # Note: Multilingual mode does not return intermediate results, need to wait for final result
                                and payload.get("audio_info", {}).get("duration", 0) > 2000
                                and not utterances
                                and not payload["result"].get("text")
                                and conn.client_listen_mode != "manual"
                            ):
                                logger.bind(tag=TAG).error(f"Recognition text: Empty")
                                self.text = ""
                                conn.reset_vad_states()
                                if len(audio_data) > 15:  # Ensure enough audio data
                                    await self.handle_voice_stop(conn, audio_data)
                                break

                            # Handle cases with no text result (Manual mode might have finished recognition but button not released)
                            elif not payload["result"].get("text") and not utterances:
                                # Multilingual mode keeps returning empty text until final result, so exclude it
                                if self.enable_multilingual:
                                    continue

                                if conn.client_listen_mode == "manual" and conn.client_voice_stop and len(audio_data) > 0:
                                    logger.bind(tag=TAG).debug("Received stop signal at end of message, trigger processing")
                                    await self.handle_voice_stop(conn, audio_data)
                                    # Clear audio cache
                                    conn.asr_audio.clear()
                                    conn.reset_vad_states()
                                    break

                            for utterance in utterances:
                                if utterance.get("definite", False):
                                    current_text = utterance["text"]
                                    logger.bind(tag=TAG).info(
                                        f"Recognized text: {current_text}"
                                    )

                                    # Accumulate recognition results in manual mode
                                    if conn.client_listen_mode == "manual":
                                        if self.text:
                                            self.text += current_text
                                        else:
                                            self.text = current_text

                                        # Received stop signal in the middle of message
                                        if conn.client_voice_stop and len(audio_data) > 0:
                                            logger.bind(tag=TAG).debug("Received stop signal in middle of message, trigger processing")
                                            await self.handle_voice_stop(conn, audio_data)
                                            # Clear audio cache
                                            conn.asr_audio.clear()
                                            conn.reset_vad_states()
                                        break
                                    else:
                                        # Overwrite directly in auto mode
                                        self.text = current_text
                                        conn.reset_vad_states()
                                        if len(audio_data) > 15:  # Ensure enough audio data
                                            await self.handle_voice_stop(conn, audio_data)
                                    break
                        elif "error" in payload:
                            error_msg = payload.get("error", "Unknown error")
                            logger.bind(tag=TAG).error(f"ASR service returned error: {error_msg}")
                            break

                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).info("ASR service connection closed")
                    self.is_processing = False
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Error processing ASR result: {str(e)}")
                    if hasattr(e, "__cause__") and e.__cause__:
                        logger.bind(tag=TAG).error(f"Error cause: {str(e.__cause__)}")
                    self.is_processing = False
                    break

        except Exception as e:
            logger.bind(tag=TAG).error(f"ASR result forwarding task error: {str(e)}")
            if hasattr(e, "__cause__") and e.__cause__:
                logger.bind(tag=TAG).error(f"Error cause: {str(e.__cause__)}")
        finally:
            if self.asr_ws:
                await self.asr_ws.close()
                self.asr_ws = None
            self.is_processing = False
            if conn:
                if hasattr(conn, 'asr_audio_for_voiceprint'):
                    conn.asr_audio_for_voiceprint = []
                if hasattr(conn, 'asr_audio'):
                    conn.asr_audio = []

    def stop_ws_connection(self):
        if self.asr_ws:
            asyncio.create_task(self.asr_ws.close())
            self.asr_ws = None
        self.is_processing = False

    async def _send_stop_request(self):
        """Send last audio frame to notify server to end"""
        if self.asr_ws:
            try:
                # Send audio frame with end marker (gzip compressed empty data)
                empty_payload = gzip.compress(b"")
                last_audio_request = bytearray(self.generate_last_audio_default_header())
                last_audio_request.extend(len(empty_payload).to_bytes(4, "big"))
                last_audio_request.extend(empty_payload)
                await self.asr_ws.send(last_audio_request)
                logger.bind(tag=TAG).debug("Sent end audio frame")
            except Exception as e:
                logger.bind(tag=TAG).debug(f"Error sending end audio frame: {e}")

    def construct_request(self, reqid):
        req = {
            "app": {
                "appid": self.appid,
                "cluster": self.cluster,
                "token": self.access_token,
            },
            "user": {"uid": self.uid},
            "request": {
                "reqid": reqid,
                "workflow": self.workflow,
                "show_utterances": True,
                "result_type": self.result_type,
                "sequence": 1,
                "boosting_table_name": self.boosting_table_name,
                "correct_table_name": self.correct_table_name,
                "end_window_size": self.end_window_size,
            },
            "audio": {
                "format": self.format,
                "codec": self.codec,
                "rate": self.rate,
                "bits": self.bits,
                "channel": self.channel,
                "sample_rate": self.rate,
            },
        }

        # language参数仅在多语种模式下添加
        if self.enable_multilingual and self.language:
            req["audio"]["language"] = self.language

        logger.bind(tag=TAG).debug(
            f"Construct request parameters: {json.dumps(req, ensure_ascii=False)}"
        )
        return req

    def token_auth(self):
        return {
            "X-Api-App-Key": self.appid,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": "volc.bigasr.sauc.duration",
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

    def generate_header(
        self,
        version=0x01,
        message_type=0x01,
        message_type_specific_flags=0x00,
        serial_method=0x01,
        compression_type=0x01,
        reserved_data=0x00,
        extension_header: bytes = b"",
    ):
        header = bytearray()
        header_size = int(len(extension_header) / 4) + 1
        header.append((version << 4) | header_size)
        header.append((message_type << 4) | message_type_specific_flags)
        header.append((serial_method << 4) | compression_type)
        header.append(reserved_data)
        header.extend(extension_header)
        return header

    def generate_audio_default_header(self):
        return self.generate_header(
            version=0x01,
            message_type=0x02,
            message_type_specific_flags=0x00,
            serial_method=0x01,
            compression_type=0x01,
        )

    def generate_last_audio_default_header(self):
        return self.generate_header(
            version=0x01,
            message_type=0x02,
            message_type_specific_flags=0x02,
            serial_method=0x01,
            compression_type=0x01,
        )

    def parse_response(self, res: bytes) -> dict:
        try:
            # Check response length
            if len(res) < 4:
                logger.bind(tag=TAG).error(f"Insufficient response data length: {len(res)}")
                return {"error": "Insufficient response data length"}

            # Get message header
            header = res[:4]
            message_type = header[1] >> 4

            # If error response
            if message_type == 0x0F:  # SERVER_ERROR_RESPONSE
                code = int.from_bytes(res[4:8], "big", signed=False)
                msg_length = int.from_bytes(res[8:12], "big", signed=False)
                error_msg = json.loads(res[12:].decode("utf-8"))
                return {
                    "code": code,
                    "msg_length": msg_length,
                    "payload_msg": error_msg,
                }

            # Get JSON data (skip 12 bytes header)
            try:
                json_data = res[12:].decode("utf-8")
                result = json.loads(json_data)
                logger.bind(tag=TAG).debug(f"Successfully parsed JSON response: {result}")
                return {"payload_msg": result}
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                logger.bind(tag=TAG).error(f"JSON parsing failed: {str(e)}")
                logger.bind(tag=TAG).error(f"Original data: {res}")
                raise

        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to parse response: {str(e)}")
            logger.bind(tag=TAG).error(f"Original response data: {res.hex()}")
            raise

    async def speech_to_text(self, opus_data, session_id, audio_format):
        result = self.text
        self.text = ""  # Clear text
        return result, None

    async def close(self):
        """资源清理方法"""
        if self.asr_ws:
            await self.asr_ws.close()
            self.asr_ws = None
        if self.forward_task:
            self.forward_task.cancel()
            try:
                await self.forward_task
            except asyncio.CancelledError:
                pass
            self.forward_task = None
        self.is_processing = False
        
        # 显式释放decoder资源
        if hasattr(self, 'decoder') and self.decoder is not None:
            try:
                del self.decoder
                self.decoder = None
                logger.bind(tag=TAG).debug("Doubao decoder resources released")
            except Exception as e:
                logger.bind(tag=TAG).debug(f"释放Doubao decoder资源时出错: {e}")

        # 清理所有连接的音频缓冲区
        if hasattr(self, '_connections'):
            for conn in self._connections.values():
                if hasattr(conn, 'asr_audio_for_voiceprint'):
                    conn.asr_audio_for_voiceprint = []
                if hasattr(conn, 'asr_audio'):
                    conn.asr_audio = []
