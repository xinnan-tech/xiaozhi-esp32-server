import json
import uuid
import asyncio
import websockets
import opuslib_next
from typing import List
from config.logger import setup_logging
from core.providers.asr.base import ASRProviderBase
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
        self.is_processing = False
        self.server_ready = False  # Server ready status
        self.task_id = None  # Current task ID

        # Aliyun Bailian configuration
        self.api_key = config.get("api_key")
        self.model = config.get("model", "paraformer-realtime-v2")
        self.sample_rate = config.get("sample_rate", 16000)
        self.format = config.get("format", "pcm")

        # Optional parameters
        self.vocabulary_id = config.get("vocabulary_id")
        self.disfluency_removal_enabled = config.get("disfluency_removal_enabled", False)
        self.language_hints = config.get("language_hints")
        self.semantic_punctuation_enabled = config.get("semantic_punctuation_enabled", False)
        max_sentence_silence = config.get("max_sentence_silence")
        self.max_sentence_silence = int(max_sentence_silence) if max_sentence_silence else 200
        self.multi_threshold_mode_enabled = config.get("multi_threshold_mode_enabled", False)
        self.punctuation_prediction_enabled = config.get("punctuation_prediction_enabled", True)
        self.inverse_text_normalization_enabled = config.get("inverse_text_normalization_enabled", True)

        # WebSocket URL
        self.ws_url = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"

        self.output_dir = config.get("output_dir", "./audio_output")
        self.delete_audio_file = delete_audio_file

    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)

    async def receive_audio(self, conn, audio, audio_have_voice):
        # Initialize audio buffer
        if not hasattr(conn, 'asr_audio_for_voiceprint'):
            conn.asr_audio_for_voiceprint = []

        # Store audio data
        if audio:
            conn.asr_audio_for_voiceprint.append(audio)

        conn.asr_audio.append(audio)
        conn.asr_audio = conn.asr_audio[-10:]

        # Establish connection only if there is voice and no connection exists
        if audio_have_voice and not self.is_processing and not self.asr_ws:
            try:
                await self._start_recognition(conn)
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to start recognition: {str(e)}")
                await self._cleanup()
                return

        # Send audio data
        if self.asr_ws and self.is_processing and self.server_ready:
            try:
                pcm_frame = self.decoder.decode(audio, 960)
                # Directly send PCM audio data (binary)
                await self.asr_ws.send(pcm_frame)
            except Exception as e:
                logger.bind(tag=TAG).warning(f"Failed to send audio: {str(e)}")
                await self._cleanup()

    async def _start_recognition(self, conn):
        """Start recognition session"""
        try:
            # If manual mode, set timeout to max value
            if conn.client_listen_mode == "manual":
                self.max_sentence_silence = 6000

            self.is_processing = True
            self.task_id = uuid.uuid4().hex

            # 建立WebSocket连接
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            logger.bind(tag=TAG).debug(f"Connecting to Aliyun Bailian ASR service, task_id: {self.task_id}")

            self.asr_ws = await websockets.connect(
                self.ws_url,
                additional_headers=headers,
                max_size=1000000000,
                ping_interval=None,
                ping_timeout=None,
                close_timeout=5,
            )

            logger.bind(tag=TAG).debug("WebSocket connection established")

            self.server_ready = False
            self.forward_task = asyncio.create_task(self._forward_results(conn))

            # Send run-task command
            run_task_msg = self._build_run_task_message()
            await self.asr_ws.send(json.dumps(run_task_msg, ensure_ascii=False))
            logger.bind(tag=TAG).debug("Sent run-task command, waiting for server preparation...")

        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to establish ASR connection: {str(e)}")
            if self.asr_ws:
                await self.asr_ws.close()
                self.asr_ws = None
            self.is_processing = False
            raise

    def _build_run_task_message(self) -> dict:
        """Build run-task command"""
        message = {
            "header": {
                "action": "run-task",
                "task_id": self.task_id,
                "streaming": "duplex"
            },
            "payload": {
                "task_group": "audio",
                "task": "asr",
                "function": "recognition",
                "model": self.model,
                "parameters": {
                    "format": self.format,
                    "sample_rate": self.sample_rate,
                    "disfluency_removal_enabled": self.disfluency_removal_enabled,
                    "semantic_punctuation_enabled": self.semantic_punctuation_enabled,
                    "max_sentence_silence": self.max_sentence_silence,
                    "multi_threshold_mode_enabled": self.multi_threshold_mode_enabled,
                    "punctuation_prediction_enabled": self.punctuation_prediction_enabled,
                    "inverse_text_normalization_enabled": self.inverse_text_normalization_enabled,
                },
                "input": {}
            }
        }

        # Add vocabulary_id only if model name ends with v2
        if self.model.lower().endswith("v2"):
            message["payload"]["parameters"]["vocabulary_id"] = self.vocabulary_id

        if self.language_hints:
            message["payload"]["parameters"]["language_hints"] = self.language_hints

        return message

    async def _forward_results(self, conn):
        """Forward recognition results"""
        try:
            while not conn.stop_event.is_set():
                try:
                    response = await asyncio.wait_for(self.asr_ws.recv(), timeout=1.0)
                    result = json.loads(response)

                    header = result.get("header", {})
                    payload = result.get("payload", {})
                    event = header.get("event", "")

                     # Handle task-started event
                    if event == "task-started":
                        self.server_ready = True
                        logger.bind(tag=TAG).debug("Server ready, starting to send cached audio...")

                        # Send cached audio
                        if conn.asr_audio:
                            for cached_audio in conn.asr_audio[-10:]:
                                try:
                                    pcm_frame = self.decoder.decode(cached_audio, 960)
                                    await self.asr_ws.send(pcm_frame)
                                except Exception as e:
                                    logger.bind(tag=TAG).warning(f"Failed to send cached audio: {e}")
                                    break
                        continue

                    # Handle result-generated event
                    elif event == "result-generated":
                        output = payload.get("output", {})
                        sentence = output.get("sentence", {})

                        text = sentence.get("text", "")
                        sentence_end = sentence.get("sentence_end", False)
                        end_time = sentence.get("end_time")

                        # Determine if it is final result (sentence_end is True and end_time is not null)
                        is_final = sentence_end and end_time is not None

                        if is_final:
                            logger.bind(tag=TAG).info(f"Recognized text: {text}")

                            # Accumulate recognition results in manual mode
                            if conn.client_listen_mode == "manual":
                                if self.text:
                                    self.text += text
                                else:
                                    self.text = text

                                # In manual mode, only trigger processing after receiving stop signal
                                if conn.client_voice_stop:
                                    audio_data = getattr(conn, 'asr_audio_for_voiceprint', [])
                                    if len(audio_data) > 0:
                                        logger.bind(tag=TAG).debug("Received final recognition result, triggering processing")
                                        await self.handle_voice_stop(conn, audio_data)
                                        # Clear audio cache
                                        conn.asr_audio.clear()
                                        conn.reset_vad_states()
                                    break
                            else:
                                # Overwrite directly in auto mode
                                self.text = text
                                conn.reset_vad_states()
                                audio_data = getattr(conn, 'asr_audio_for_voiceprint', [])
                                await self.handle_voice_stop(conn, audio_data)
                                break

                    # Handle task-finished event
                    elif event == "task-finished":
                        logger.bind(tag=TAG).debug("Task finished")
                        break

                    # Handle task-failed event
                    elif event == "task-failed":
                        error_code = header.get("error_code", "UNKNOWN")
                        error_message = header.get("error_message", "Unknown error")
                        logger.bind(tag=TAG).error(f"Task failed: {error_code} - {error_message}")
                        break

                except asyncio.TimeoutError:
                    continue
                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).info("ASR service connection closed")
                    self.is_processing = False
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Result processing failed: {str(e)}")
                    break

        except Exception as e:
            logger.bind(tag=TAG).error(f"Result forwarding failed: {str(e)}")
        finally:
            # Clean up connected audio cache
            await self._cleanup()
            if conn:
                if hasattr(conn, 'asr_audio_for_voiceprint'):
                    conn.asr_audio_for_voiceprint = []
                if hasattr(conn, 'asr_audio'):
                    conn.asr_audio = []

    async def _send_stop_request(self):
        """Send stop request (for manual mode stop recording)"""
        if self.asr_ws:
            try:
                # Stop sending audio first
                self.is_processing = False

                logger.bind(tag=TAG).debug("Received stop request, sending finish-task command")
                await self._send_finish_task()
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to send stop request: {e}")

    async def _send_finish_task(self):
        """Send finish-task command"""
        if self.asr_ws and self.task_id:
            try:
                finish_msg = {
                    "header": {
                        "action": "finish-task",
                        "task_id": self.task_id,
                        "streaming": "duplex"
                    },
                    "payload": {
                        "input": {}
                    }
                }
                await self.asr_ws.send(json.dumps(finish_msg, ensure_ascii=False))
                logger.bind(tag=TAG).debug("Sent finish-task command")
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to send finish-task command: {e}")

    async def _cleanup(self):
        """Cleanup resources"""
        logger.bind(tag=TAG).debug(f"Starting ASR session cleanup | Current Status: processing={self.is_processing}, server_ready={self.server_ready}")

        # Reset status
        self.is_processing = False
        self.server_ready = False
        logger.bind(tag=TAG).debug("ASR status reset")

        # 关闭连接
        if self.asr_ws:
            try:
                # Send finish-task command first
                await self._send_finish_task()
                # Wait for server to process
                await asyncio.sleep(0.1)

                logger.bind(tag=TAG).debug("Closing WebSocket connection")
                await asyncio.wait_for(self.asr_ws.close(), timeout=2.0)
                logger.bind(tag=TAG).debug("WebSocket connection closed")
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to close WebSocket connection: {e}")
            finally:
                self.asr_ws = None

        # Clean up task reference
        self.forward_task = None
        self.task_id = None

        logger.bind(tag=TAG).debug("ASR session cleanup completed")

    async def speech_to_text(self, opus_data, session_id, audio_format):
        """Get recognition result"""
        result = self.text
        self.text = ""
        return result, None

    async def close(self):
        """Close resources"""
        await self._cleanup()
        if hasattr(self, 'decoder') and self.decoder is not None:
            try:
                del self.decoder
                self.decoder = None
                logger.bind(tag=TAG).debug("Aliyun BL decoder resources released")
            except Exception as e:
                logger.bind(tag=TAG).debug(f"Error releasing Aliyun BL decoder resources: {e}")