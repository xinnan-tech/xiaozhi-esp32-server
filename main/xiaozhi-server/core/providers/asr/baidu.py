import time
import os
from typing import Optional, Tuple, List
from aip import AipSpeech
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()

class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool = True):
        super().__init__()
        self.interface_type = InterfaceType.NON_STREAM
        self.app_id = config.get("app_id")
        self.api_key = config.get("api_key")
        self.secret_key = config.get("secret_key")
        dev_pid = config.get("dev_pid", "1537")
        self.dev_pid = int(dev_pid) if dev_pid else 1537
        self.output_dir = config.get("output_dir")
        self.delete_audio_file = delete_audio_file
        
        self.client = AipSpeech(str(self.app_id), self.api_key, self.secret_key)
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert speech data to text"""
        if not opus_data:
            logger.bind(tag=TAG).warning("Audio data is empty!")
            return None, None
        
        file_path = None
        try:
            # Check if configuration is set
            if not self.app_id or not self.api_key or not self.secret_key:
                logger.bind(tag=TAG).error("Baidu speech recognition configuration not set, cannot perform recognition")
                return None, file_path
            
            # Decode Opus audio data to PCM
            if audio_format == "pcm":
                pcm_data = opus_data
            else:
                pcm_data = self.decode_opus(opus_data)
            
            combined_pcm_data = b"".join(pcm_data)
            
            # Determine whether to save as WAV file
            if self.delete_audio_file:
                pass
            else:
                self.save_audio_to_file(pcm_data, session_id)
            
            start_time = time.time()
            
            # Recognize local file
            result = self.client.asr(
                combined_pcm_data,
                "pcm",
                16000,
                {
                    "dev_pid": str(self.dev_pid),
                },
            )
            
            if result and result["err_no"] == 0:
                logger.bind(tag=TAG).debug(
                    f"Baidu speech recognition time: {time.time() - start_time:.3f}s | Result: {result}"
                )
                result = result["result"][0]
                return result, file_path
            else:
                raise Exception(
                    f"Baidu speech recognition failed, error code: {result['err_no']}, error message: {result['err_msg']}"
                )
            
            return None, file_path
        
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error occurred while processing audio! {e}", exc_info=True)
            return None, file_path
