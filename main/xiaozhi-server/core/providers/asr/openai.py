import time
import os

from openai.types.audio import transcription
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.dto.dto import InterfaceType
from core.providers.asr.base import ASRProviderBase

from openai import OpenAI
from openai.types.audio import Transcription
TAG = __name__
logger = setup_logging()

class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        self.interface_type = InterfaceType.NON_STREAM
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url")
        self.model = config.get("model_name")        
        self.output_dir = config.get("output_dir")
        self.delete_audio_file = delete_audio_file

        self._client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        os.makedirs(self.output_dir, exist_ok=True)

    async def speech_to_text(self, opus_data: List[bytes], session_id: str, audio_format="opus") -> Tuple[Optional[str], Optional[str]]:
        file_path = None
        try:
            start_time = time.time()
            if audio_format == "pcm":
                pcm_data = opus_data
            else:
                pcm_data = self.decode_opus(opus_data)
            file_path = self.save_audio_to_file(pcm_data, session_id)

            logger.bind(tag=TAG).debug(
                f"Audio file save latency: {time.time() - start_time:.3f}s | Path: {file_path}"
            )

            with open(file_path, "rb") as audio_file:  # with open to ensure file is closed

                start_time = time.time()
                transcription: str = self._client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    response_format="text"
                )
                logger.bind(tag=TAG).debug(
                    f"Audio transcription latency: {time.time() - start_time:.3f}s | Result: {transcription}"
                )

            return transcription, file_path
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"Audio transcription failed: {e}")
            return "", None
        finally:
            # 文件清理逻辑
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.bind(tag=TAG).debug(f"已删除临时音频文件: {file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"文件删除失败: {file_path} | 错误: {e}")
        
