from abc import ABC, abstractmethod
from typing import Optional, Tuple, List
import opuslib_next
from config.logger import setup_logging
import os

TAG = __name__
logger = setup_logging()


class SpeakerProviderBase(ABC):
    def __init__(self):
        self.audio_format = "opus"
        self.output_dir = "tmp"
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)


    @abstractmethod
    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """PCM数据保存为WAV文件"""
        pass


    async def handle_audio_data(
        self, opus_data: List[bytes], session_id: str
    ) -> Tuple[Optional[bool], Optional[float]]:
        """验证说话人"""
        try:
            # 合并所有opus数据包
            if self.audio_format == "pcm":
                pcm_data = opus_data
            else:
                pcm_data = self.decode_opus(opus_data)
            combined_pcm_data = b"".join(pcm_data)

            # 判断是否保存为WAV文件
            file_path = self.save_audio_to_file(pcm_data, session_id)

            return self.verify_voice(file_path,combined_pcm_data, session_id)

        except Exception as e:
            logger.bind(tag=TAG).error(f"语音识别失败: {e}", exc_info=True)
            return False, 0.0

    @abstractmethod
    def verify_voice(
        self, file_path: str,audio_data: List[bytes], session_id: str
    ) -> Tuple[Optional[bool], Optional[float]]:
        """验证说话人处理逻辑"""
        pass

    def set_audio_format(self, format: str) -> None:
        """设置音频格式"""
        self.audio_format = format

    @staticmethod
    def decode_opus(opus_data: List[bytes]) -> bytes:
        """将Opus音频数据解码为PCM数据"""
        try:
            decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
            pcm_data = []
            buffer_size = 960  # 每次处理960个采样点

            for opus_packet in opus_data:
                try:
                    # 使用较小的缓冲区大小进行处理
                    pcm_frame = decoder.decode(opus_packet, buffer_size)
                    if pcm_frame:
                        pcm_data.append(pcm_frame)
                except opuslib_next.OpusError as e:
                    logger.bind(tag=TAG).warning(f"Opus解码错误，跳过当前数据包: {e}")
                    continue
                except Exception as e:
                    logger.bind(tag=TAG).error(f"音频处理错误: {e}", exc_info=True)
                    continue

            return pcm_data
        except Exception as e:
            logger.bind(tag=TAG).error(f"音频解码过程发生错误: {e}", exc_info=True)
            return []
