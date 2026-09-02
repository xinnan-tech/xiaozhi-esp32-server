import os
import io
import sys
import time
import shutil
import psutil
import asyncio

from funasr import AutoModel
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.utils import lang_tag_filter
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()

MAX_RETRIES = 2
RETRY_DELAY = 1  # Retry delay (seconds)


# Capture standard output
class CaptureOutput:
    def __enter__(self):
        self._output = io.StringIO()
        self._original_stdout = sys.stdout
        sys.stdout = self._output

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self._original_stdout
        self.output = self._output.getvalue()
        self._output.close()

        # Output captured content via logger
        if self.output:
            logger.bind(tag=TAG).info(self.output.strip())


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        
        # Memory check, requires > 2G
        min_mem_bytes = 2 * 1024 * 1024 * 1024
        total_mem = psutil.virtual_memory().total
        if total_mem < min_mem_bytes:
            logger.bind(tag=TAG).error(f"Available memory less than 2G, currently only {total_mem / (1024*1024):.2f} MB, FunASR might not start")
        
        self.interface_type = InterfaceType.LOCAL
        self.model_dir = config.get("model_dir")
        self.output_dir = config.get("output_dir")  # Correct config key name
        self.device = config.get("device", "cpu")
        self.delete_audio_file = delete_audio_file

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
        with CaptureOutput():
            self.model = AutoModel(
                model=self.model_dir,
                vad_kwargs={"max_single_segment_time": 30000},
                disable_update=True,
                hub="ms",
                device=self.device,
            )

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus", client_id: str = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Main speech-to-text processing logic"""
        file_path = None
        retry_count = 0

        while retry_count < MAX_RETRIES:
            try:
                # Merge all Opus packets
                if audio_format == "pcm":
                    pcm_data = opus_data
                else:
                    pcm_data = self.decode_opus(opus_data)

                combined_pcm_data = b"".join(pcm_data)

                # Check disk space
                if not self.delete_audio_file:
                    free_space = shutil.disk_usage(self.output_dir).free
                    if free_space < len(combined_pcm_data) * 2:  # Reserve 2x space
                        raise OSError("Insufficient disk space")

                # Determine whether to save as WAV file
                if self.delete_audio_file:
                    pass
                else:
                    file_path = self.save_audio_background(pcm_data, session_id, client_id=client_id)

                # Speech recognition - use thread pool to avoid blocking event loop
                start_time = time.time()
                result = await asyncio.to_thread(
                    self.model.generate,
                    input=combined_pcm_data,
                    cache={},
                    language="auto",
                    use_itn=True,
                    batch_size_s=60,
                )
                # Parse content based on different model return structures
                raw_text = ""
                if isinstance(result, list) and len(result) > 0:
                    item = result[0]
                    if isinstance(item, dict):
                        raw_text = item.get("text", "")
                    elif isinstance(item, str):
                        raw_text = item
                    else:
                        raw_text = str(item)
                elif isinstance(result, dict):
                    raw_text = result.get("text", "")
                else:
                    raw_text = str(result)
                
                text = lang_tag_filter(raw_text)
                
                log_content = text["content"] if isinstance(text, dict) else text
                logger.bind(tag=TAG).debug(
                    f"Speech recognition time: {time.time() - start_time:.3f}s | Result: {log_content}"
                )

                return text, file_path

            except OSError as e:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    logger.bind(tag=TAG).error(
                        f"Speech recognition failed (retried {retry_count} times): {e}", exc_info=True
                    )
                    return "", file_path
                logger.bind(tag=TAG).warning(
                    f"Speech recognition failed, retrying ({retry_count}/{MAX_RETRIES}): {e}"
                )
                time.sleep(RETRY_DELAY)

            except Exception as e:
                logger.bind(tag=TAG).error(f"Speech recognition failed: {e}", exc_info=True)
                return "", file_path

            finally:
                # File cleanup logic
                if self.delete_audio_file and file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.bind(tag=TAG).debug(f"Deleted temp audio file: {file_path}")
                    except Exception as e:
                        logger.bind(tag=TAG).error(
                            f"File deletion failed: {file_path} | Error: {e}"
                        )
