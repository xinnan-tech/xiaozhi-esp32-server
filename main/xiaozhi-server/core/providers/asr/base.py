from abc import ABC, abstractmethod
from typing import Optional, Tuple, List
import opuslib_next
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class ASRProviderBase(ABC):
    def __init__(self):
        self.audio_format = "opus"

    @abstractmethod
    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """PCM数据保存为WAV文件"""
        pass

    @abstractmethod
    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""
        pass

    def set_audio_format(self, format: str) -> None:
        """设置音频格式"""
        self.audio_format = format

    @staticmethod
    def decode_opus(opus_data: List[bytes]) -> bytes:
        """将Opus音频数据解码为PCM数据"""

        decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
        pcm_data = []

        for opus_packet in opus_data:
            try:
                pcm_frame = decoder.decode(opus_packet, 960)  # 960 samples = 60ms
                pcm_data.append(pcm_frame)
            except opuslib_next.OpusError as e:
                logger.bind(tag=TAG).error(f"Opus解码错误: {e}", exc_info=True)

        return pcm_data
