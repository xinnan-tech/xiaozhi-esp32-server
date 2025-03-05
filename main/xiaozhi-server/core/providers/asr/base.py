from abc import ABC, abstractmethod
from typing import Optional, Tuple, List

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class ASRProviderBase(ABC):
    @abstractmethod
    def save_audio_to_file(self, opus_data: List[bytes], session_id: str) -> str:
        """解码Opus数据并保存为WAV文件"""
        pass

    @abstractmethod
    async def speech_to_text(self, opus_data: List[bytes], session_id: str) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""
        pass
