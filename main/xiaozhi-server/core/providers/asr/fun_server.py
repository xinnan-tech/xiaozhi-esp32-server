from typing import Optional, Tuple, List
import opuslib_next
from core.providers.asr.base import ASRProviderBase
import os
import ssl
import json
import uuid
import wave
import websockets
from config.logger import setup_logging
import asyncio
import re

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        """
        Initialize the ASRProvider with server configuration.
        :param config: Dictionary containing 'host', 'port', and 'is_ssl'.
        :param delete_audio_file: Boolean to indicate whether to delete audio files after processing.
        """
        super().__init__()
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 10095)
        self.api_key = config.get("api_key", "none")
        self.is_ssl = str(config.get("is_ssl", True)).lower() in (
            "true",
            "1",
            "yes",
        )
        self.output_dir = config.get("output_dir")
        self.delete_audio_file = delete_audio_file
        self.uri = (
            f"wss://{self.host}:{self.port}"
            if self.is_ssl
            else f"ws://{self.host}:{self.port}"
        )
        self.ssl_context = ssl.SSLContext() if self.is_ssl else None
        if self.ssl_context:
            self.ssl_context.check_hostname = False
            self.ssl_context.verify_mode = ssl.CERT_NONE

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """PCM数据保存为WAV文件"""
        module_name = __name__.split(".")[-1]
        file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    async def _receive_responses(self, ws) -> None:
        """
        Asynchronous generator to receive messages from the WebSocket.
        Yields each message as it is received.
        """
        text = ""
        while True:
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                response_data = json.loads(response)
                logger.bind(tag=TAG).debug(f"Received response: {response_data}")
                if response_data.get("is_final", True):
                    text += response_data.get("text", "")
                    break
                else:
                    text += response_data.get("text", "")
            except asyncio.TimeoutError:
                logger.bind(tag=TAG).error(
                    "Timeout while waiting for response from WebSocket."
                )
                break
            except websockets.exceptions.ConnectionClosed as e:
                logger.bind(tag=TAG).error(f"WebSocket connection closed: {e}")
                break
        return text

    async def _send_data(self, ws, pcm_data: bytes, session_id: str) -> tuple:
        """
        Internal method to handle WebSocket communication.
        Reuses the persistent WebSocket connection if available.
        :param pcm_data: PCM audio data to send.
        :param session_id: Unique session identifier.
        :return: Tuple containing recognized text and optional timestamp.
        """

        # Send initial configuration message
        config_message = json.dumps(
            {
                "mode": "offline",
                "chunk_size": [5, 10, 5],
                "chunk_interval": 10,
                "wav_name": session_id,
                "is_speaking": True,
                "itn": False,
            }
        )
        await ws.send(config_message)
        logger.bind(tag=TAG).debug(f"Sent configuration message: {config_message}")

        # Send PCM data
        await ws.send(pcm_data)
        logger.bind(tag=TAG).debug(f"Sent PCM data of length: {len(pcm_data)} bytes")

        # Indicate end of speech
        end_message = json.dumps({"is_speaking": False})
        await ws.send(end_message)
        logger.bind(tag=TAG).debug(f"Sent end message: {end_message}")

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Convert speech data to text using FunASR.
        :param opus_data: List of Opus-encoded audio data chunks.
        :param session_id: Unique session identifier.
        :return: Tuple containing recognized text and optional timestamp.
        """
        file_path = None
        if self.audio_format == "pcm":
            pcm_data = opus_data
        else:
            pcm_data = self.decode_opus(opus_data)
        combined_pcm_data = b"".join(pcm_data)

        # 判断是否保存为WAV文件
        if self.delete_audio_file:
            pass
        else:
            file_path = self.save_audio_to_file(pcm_data, session_id)
        auth_header = {"Authorization": "Bearer; {}".format(self.api_key)}
        async with websockets.connect(
            self.uri,
            additional_headers=auth_header,
            subprotocols=["binary"],
            ping_interval=None,
            ssl=self.ssl_context,
        ) as ws:
            try:
                # Use asyncio to handle WebSocket communication
                send_task = asyncio.create_task(
                    self._send_data(ws, combined_pcm_data, session_id)
                )
                receive_task = asyncio.create_task(self._receive_responses(ws))

                # Gather tasks with error handling
                done, pending = await asyncio.wait(
                    [send_task, receive_task], return_when=asyncio.FIRST_EXCEPTION
                )

                # Cancel any pending tasks
                for task in pending:
                    task.cancel()

                # Check for exceptions in completed tasks
                for task in done:
                    if task.exception():
                        raise task.exception()

                # Get the result from the receive task
                result = receive_task.result()
                match = re.match(r"<\|(.*?)\|><\|(.*?)\|><\|(.*?)\|>(.*)", result)
                if match:
                    result = match.group(4).strip()
                return (
                    result,
                    file_path,
                )  # Return the recognized text and timestamp (if any)

            except websockets.exceptions.ConnectionClosed as e:
                logger.bind(tag=TAG).error(f"WebSocket connection closed: {e}")
                return "", file_path
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"Error during speech-to-text conversion: {e}", exc_info=True
                )
                return "", file_path
