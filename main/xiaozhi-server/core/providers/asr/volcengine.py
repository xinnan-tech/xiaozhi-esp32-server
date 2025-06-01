import time
import io
import wave
import os
from typing import Optional, Tuple, List
import uuid
import websockets
import json
import base64

import opuslib_next
from core.providers.asr.base import ASRProviderBase

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        self.api_key = config.get("api_key")
        self.model_name = config.get("model_name")
        self.output_dir = config.get("output_dir")
        self.host = config.get("host")
        if self.host is None:
            self.host = "ai-gateway.vei.volces.com"
        if self.output_dir is None:
            self.output_dir = "tmp/"
        self.delete_audio_file = delete_audio_file
        self.ws_url = f"wss://{self.host}/v1/realtime?model={self.model_name}"
        self.success_code = 1000
        self.seg_duration = 15000

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

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

    async def _receive_messages(self, client) -> Optional[str]:
        resp_msg = ""
        while True:
            message = await client.recv()
            event = json.loads(message)
            logger.bind(tag=TAG).debug(f"received raw message: {message}")
            message_type = event.get("type")
            if message_type == 'conversation.item.input_audio_transcription.completed':
                logger.bind(tag=TAG).debug(f"responsed message: {resp_msg}")
                return resp_msg
            elif message_type == 'conversation.item.input_audio_transcription.result':
                resp_msg += event.get("transcript")


    def _create_session_msg(self):
        config = {
            "input_audio_format": "pcm",
            "input_audio_codec": "raw",
            "input_audio_sample_rate": 16000,
            "input_audio_bits": 16,
            "input_audio_channel": 1,
            "input_audio_transcription": {
                "model": self.model_name
            },
        }
        event = {
            "type": "transcription_session.update",
            "session": config
        }
        return json.dumps(event)

    async def _send_request(
        self, audio_data: List[bytes], segment_size: int
    ) -> Optional[str]:
        """Send request to Volc LLM gateway ASR service."""
        try:
            auth_header = {"Authorization": f"Bearer {self.api_key}"}
            logger.bind(tag=TAG).info(f"ASR 参数: {self.ws_url} {auth_header} ")
            async with websockets.connect(
                self.ws_url, additional_headers=auth_header
            ) as websocket:
                # Prepare request data
                create_session_msg = self._create_session_msg()

                # Send header and metadata
                # full_client_request
                await websocket.send(create_session_msg)
                

                for _, (chunk, last) in enumerate(
                    self.slice_data(audio_data, segment_size), 1
                ):
                    base64_audio = base64.b64encode(chunk).decode("utf-8")
                    if last:
                        # 最后一个包，支持commit
                        ws_event = {
                            "audio": base64_audio,
                            "type": "input_audio_buffer.append"
                        }
                    else:
                        ws_event = {
                            "type": "input_audio_buffer.append",
                            "audio": base64_audio
                        }
                
                    # Send audio data
                    await websocket.send(json.dumps(ws_event))

                # Send commit event    
                ws_event = {
                    "type": "input_audio_buffer.commit"
                 }
                await websocket.send(json.dumps(ws_event))
                # Receive response
                return await self._receive_messages(websocket)
        except Exception as e:
            logger.bind(tag=TAG).error(f"ASR request failed: {e}", exc_info=True)
            return None

    @staticmethod
    def slice_data(data: bytes, chunk_size: int) -> (list, bool):
        """
        slice data
        :param data: wav data
        :param chunk_size: the segment size in one request
        :return: segment data, last flag
        """
        data_len = len(data)
        offset = 0
        while offset + chunk_size < data_len:
            yield data[offset : offset + chunk_size], False
            offset += chunk_size
        else:
            yield data[offset:data_len], True

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""

        file_path = None
        try:
            # 合并所有opus数据包
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

            # 直接使用PCM数据
            # 计算分段大小 (单声道, 16bit, 16kHz采样率)
            size_per_sec = 1 * 2 * 16000  # nchannels * sampwidth * framerate
            segment_size = int(size_per_sec * self.seg_duration / 1000)

            # 语音识别
            start_time = time.time()
            text = await self._send_request(combined_pcm_data, segment_size)
            if text:
                logger.bind(tag=TAG).debug(
                    f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {text}"
                )
                return text, file_path
            return "", file_path

        except Exception as e:
            logger.bind(tag=TAG).error(f"语音识别失败: {e}", exc_info=True)
            return "", file_path