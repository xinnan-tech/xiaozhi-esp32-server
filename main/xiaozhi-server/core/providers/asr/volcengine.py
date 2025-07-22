"""
This module provides the ASR (Automatic Speech Recognition) provider for the Volcengine service.
It implements a streaming ASR client that connects to the Volcengine ASR service via WebSocket.
"""

import asyncio
import base64
import json
import os
import uuid
from typing import List, Optional, Tuple

import opuslib_next
import websockets

from config.logger import setup_logging
from core.handle.receiveAudioHandle import startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType
from core.utils.util import remove_punctuation_and_length

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    """
    Implements a streaming ASR provider for Volcengine, inheriting from ASRProviderBase.

    This class manages a WebSocket connection to the Volcengine ASR service for real-time
    speech-to-text transcription. It handles audio data processing, session management,
    and result forwarding.
    """

    def __init__(self, config: dict, delete_audio_file: bool):
        """
        Initializes the ASRProvider for Volcengine.

        Args:
            config (dict): A dictionary containing configuration parameters such as
                           api_key, model_name, output_dir, and host.
            delete_audio_file (bool): Flag to determine if audio files should be deleted
                                      after processing.
        """
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.api_key = config.get("api_key")
        self.model_name = config.get("model_name")
        self.output_dir = config.get("output_dir", "tmp/")
        self.host = config.get("host", "ai-gateway.vei.volces.com")
        self.delete_audio_file = delete_audio_file
        self.ws_url = f"wss://{self.host}/v1/realtime?model={self.model_name}"
        self.success_code = 1000
        self.seg_duration = 15000

        # Ensure the output directory exists.
        os.makedirs(self.output_dir, exist_ok=True)

        # State variables for streaming processing.
        self.ws = None
        self.conn = None
        # 客户端发送任务结束修改状态
        self.session_started = False
        # 客户端接收任务结束修改状态
        self.is_processing: bool = False
        self.forward_task: Optional[asyncio.Task] = None
        self.text: str = ""  # Stores the currently recognized text.
        self.decoder = opuslib_next.Decoder(16000, 1)  # Opus decoder if input is opus.
        self.current_session_id: Optional[str] = None
        self.audio_buffer = bytearray()  # Buffer for audio data.

    async def open_audio_channels(self, conn):
        """
        Opens audio channels and initializes the session.

        Args:
            conn: The connection object, which includes session details.
        """
        await super().open_audio_channels(conn)
        await self._ensure_connection()
        self.conn = conn

    async def receive_audio(self, conn, audio: bytes, audio_have_voice: bool):
        """
        Receives and processes incoming audio data.

        This method buffers audio, detects voice activity, and initiates the ASR session
        when voice is detected. It sends audio chunks to the ASR service for processing.

        Args:
            conn: The connection object.
            audio (bytes): The raw audio data chunk.
            audio_have_voice (bool): Flag indicating if the current audio chunk contains voice.
        """
        # Buffer audio; discard old audio if there's no voice.
        conn.asr_audio.append(audio)
        conn.asr_audio = conn.asr_audio[-10:]

        # Start a new ASR session if voice is detected and not already processing.
        if audio_have_voice and not self.is_processing:
            try:
                self.is_processing = True
                await self.start_session()
                pcm_frame = self.decode_opus(conn.asr_audio)
                await self._send_audio_chunk(b"".join(pcm_frame))
                conn.asr_audio.clear()
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Failed to establish ASR connection: {e}", exc_info=True
                )
                await self.stop_ws_connection()
                return

        # Send the current audio data if the session is active.
        if self.ws and self.is_processing:
            try:
                logger.bind(tag=TAG).debug(
                    f"Sending audio data, size: {len(audio)} for session: {self.current_session_id}"
                )
                pcm_frame = self.decode_opus(conn.asr_audio)
                await self._send_audio_chunk(b"".join(pcm_frame))
                conn.asr_audio.clear()
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Error sending audio data: {e}", exc_info=True
                )
                await self.stop_ws_connection()
        # Finish the session if end-of-utterance is detected.
        if self.ws and self.session_started and self.is_eou(conn, self.text):
            logger.bind(tag=TAG).info(f"Finishing session: {self.current_session_id}")
            await self.finish_session()

    async def _send_audio_chunk(self, pcm_data: bytes):
        """
        Sends a chunk of PCM audio data to the ASR service.

        The audio data is Base64-encoded and sent as a JSON message over the WebSocket.

        Args:
            pcm_data (bytes): The PCM audio data to send.
        """
        if not self.ws or not self.is_processing:
            return

        # The Volcengine streaming ASR service expects Base64-encoded PCM data.
        base64_audio = base64.b64encode(pcm_data).decode("utf-8")
        audio_event = {"audio": base64_audio, "type": "input_audio_buffer.append"}
        await self.ws.send(json.dumps(audio_event))
        logger.bind(tag=TAG).debug(f"Sent audio chunk, size: {len(pcm_data)}")

    async def _forward_asr_results(self):
        """
        Listens for and processes incoming messages from the ASR service.

        This method runs in a background task, continuously receiving ASR results,
        updating the recognized text, and handling final transcripts.
        """
        try:
            logger.bind(tag=TAG).debug(
                f"ASR forwarder started for session: {self.current_session_id}"
            )
            while self.ws and not self.conn.stop_event.is_set() and self.is_processing:
                try:
                    message = await self.ws.recv()
                    event = json.loads(message)
                    logger.bind(tag=TAG).debug(
                        f"Received ASR result for session {self.current_session_id}: {event}"
                    )

                    # Parse the response from the Volcengine streaming ASR service.
                    message_type = event.get("type")
                    if (
                        message_type
                        == "conversation.item.input_audio_transcription.result"
                    ):
                        transcript_segment = event.get("transcript", "")
                        is_final = event.get("is_final", False)
                        self.text = transcript_segment  # Append intermediate result.
                        if is_final:
                            logger.bind(tag=TAG).info(f"Final ASR result: {self.text}")
                            self.conn.reset_vad_states()
                            await self.handle_voice_stop(self.conn, None)
                    elif (
                        message_type
                        == "conversation.item.input_audio_transcription.completed"
                    ):
                        final_transcript = event.get("transcript", self.text)
                        logger.bind(tag=TAG).info(
                            f"ASR transcription completed: {final_transcript}"
                        )
                        self.text = final_transcript  # Ensure final result is used.
                        self.conn.reset_vad_states()
                        await self.handle_voice_stop(self.conn, None)
                        self.text = ""  # Reset for next utterance.
                        break  # End the receiving task.
                    elif message_type == "error":
                        error_msg = event.get("error", {})
                        logger.bind(tag=TAG).error(f"ASR service error: {error_msg}")
                        break

                except websockets.ConnectionClosed:
                    await self.stop_ws_connection()
                    logger.bind(tag=TAG).error("ASR WebSocket connection closed.")
                    break
                except json.JSONDecodeError:
                    logger.bind(tag=TAG).error(
                        f"Failed to decode JSON from ASR: {message}"
                    )
                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"Error processing ASR result: {e}", exc_info=True
                    )
                    break
        finally:
            logger.bind(tag=TAG).debug(
                f"ASR forwarder task finished for session: {self.current_session_id}"
            )
            self.is_processing = False

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        In streaming mode, this method returns the currently recognized text.
        The final result is handled by the `_forward_asr_results` method.

        Args:
            opus_data (List[bytes]): List of Opus audio data chunks.
            session_id (str): The ID of the current session.
            audio_format (str): The format of the audio data.

        Returns:
            A tuple containing the recognized text and None.
        """
        return self.text, None

    async def start_session(self):
        """
        Starts a new ASR transcription session.

        This involves ensuring a WebSocket connection is active, sending a session
        start request, and creating a task to listen for ASR results.

        Args:
            session_id (str): The unique identifier for the session.

        Raises:
            Exception: If the session fails to start.
        """
        self.current_session_id = uuid.uuid4().hex
        logger.bind(tag=TAG).info(f"Starting session {self.current_session_id}")
        try:
            await self._ensure_connection()
            # Create the request message to start streaming recognition.
            config = {
                "input_audio_format": "pcm",
                "input_audio_codec": "raw",
                "input_audio_sample_rate": 16000,
                "input_audio_bits": 16,
                "input_audio_channel": 1,
                "input_audio_transcription": {"model": self.model_name},
                "session_id": self.current_session_id,
            }
            event = {"type": "transcription_session.update", "session": config}
            await self.ws.send(json.dumps(event))
            self.session_started = True
            logger.bind(tag=TAG).debug(f"Session start request sent: {event}")

            # Start the task to listen for results.
            if self.forward_task is None:
                self.forward_task = asyncio.create_task(self._forward_asr_results())
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to start session: {e}")
            if self.forward_task:
                self.forward_task.cancel()
                try:
                    await self.forward_task
                except asyncio.CancelledError:
                    pass
                self.forward_task = None
            await self.stop_ws_connection()
            raise

    async def finish_session(self):
        """
        Finishes the current ASR session.

        Sends a commit message to the service to finalize the transcription and waits
        for the result forwarding task to complete.

        Args:
            session_id (str): The ID of the session to finish.
        """
        logger.bind(tag=TAG).info(f"Stopping session {self.current_session_id}")
        try:
            self.audio_buffer.clear()
            done_payload = {"type": "input_audio_buffer.commit"}
            await self.ws.send(json.dumps(done_payload))
            self.session_started = False
            logger.bind(tag=TAG).debug(
                f"Session finish: {done_payload} for session: {self.current_session_id}"
            )
        except Exception as e:
            await self.stop_ws_connection()
            logger.bind(tag=TAG).error(f"Failed to close session: {e}")

        # Wait for the forwarding task to complete.
        if self.forward_task:
            try:
                await self.forward_task
                logger.bind(tag=TAG).debug("Forwarding task has completed.")
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error waiting for forwarding task: {e}")
            finally:
                self.forward_task = None
                self.current_session_id = None

    async def handle_voice_stop(self, conn, asr_audio_task):
        """
        Handles the event when voice activity stops.

        Retrieves the final recognized text and initiates the chat process.

        Args:
            conn: The connection object.
            asr_audio_task: The audio task associated with the ASR.
        """
        raw_text, _ = await self.speech_to_text(
            asr_audio_task, conn.session_id, conn.audio_format
        )
        conn.logger.bind(tag=TAG).info(f"Recognized text: {raw_text}")
        text_len, _ = remove_punctuation_and_length(raw_text)
        if text_len > 0:
            await startToChat(conn, raw_text)
            enqueue_asr_report(conn, raw_text, asr_audio_task)

    async def _ensure_connection(self):
        """
        Ensures that the WebSocket connection to the ASR service is active.

        If the connection is down, it attempts to reconnect.

        Raises:
            Exception: If the connection cannot be established.
        """
        # 检查连接是否存在且处于 open 状态
        # websockets 库的自动 ping/pong 机制会处理连接健康检查
        if self.ws:
            logger.bind(tag=TAG).debug("WebSocket connection is active.")
            return

        # 如果连接不存在或已关闭，则重新连接
        try:
            logger.bind(tag=TAG).info(f"Connecting to {self.ws_url}")
            headers = {"Authorization": f"Bearer {self.api_key}"}
            # 使用内置的 ping/pong 机制来维持连接和检查健康状况
            # 每 60 秒发送一次 ping，等待 30 秒超时
            self.ws = await websockets.connect(
                self.ws_url,
                additional_headers=headers,
                ping_interval=60,  # Increased from 20
                ping_timeout=30,  # Increased from 10
                close_timeout=10,  # Added for graceful close
            )
            logger.bind(tag=TAG).info("WebSocket connection established.")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to connect to WebSocket: {e}")
            self.ws = None
            raise

    async def stop_ws_connection(self):
        """
        Stops the WebSocket connection gracefully.
        """
        logger.bind(tag=TAG).info("Stopping ASR WebSocket connection...")
        if self.ws:
            try:
                await self.ws.close()
                logger.bind(tag=TAG).info(
                    "ASR WebSocket connection closed successfully."
                )
            except websockets.WebSocketException as e:
                logger.bind(tag=TAG).error(f"Error closing ASR WebSocket: {e}")
            finally:
                self.ws = None
