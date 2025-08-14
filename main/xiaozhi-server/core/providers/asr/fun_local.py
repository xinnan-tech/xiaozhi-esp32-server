import time
import os
import sys
import io
import psutil
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.base import ASRProviderBase
from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess
import shutil
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

        # Output captured content through logger
        if self.output:
            logger.bind(tag=TAG).info(self.output.strip())


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()

        # Memory detection, require more than 2G
        min_mem_bytes = 2 * 1024 * 1024 * 1024
        total_mem = psutil.virtual_memory().total
        if total_mem < min_mem_bytes:
            logger.bind(tag=TAG).error(
                f"Insufficient memory (less than 2G), currently only {total_mem / (1024*1024):.2f} MB available, may not be able to start FunASR")

        self.interface_type = InterfaceType.LOCAL
        self.model_dir = config.get("model_dir")
        # Correct configuration key name
        self.output_dir = config.get("output_dir")
        self.delete_audio_file = delete_audio_file

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        with CaptureOutput():
            self.model = AutoModel(
                model=self.model_dir,
                vad_kwargs={"max_single_segment_time": 30000},
                disable_update=True,
                hub="hf",
                # device="cuda:0",  # Enable GPU acceleration
            )

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Speech to text main processing logic"""
        file_path = None
        retry_count = 0

        while retry_count < MAX_RETRIES:
            try:
                # Merge all opus data packets
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
                    file_path = self.save_audio_to_file(pcm_data, session_id)

                # Speech recognition
                start_time = time.time()
                result = self.model.generate(
                    input=combined_pcm_data,
                    cache={},
                    language="auto",
                    use_itn=True,
                    batch_size_s=60,
                )

                text = rich_transcription_postprocess(result[0]["text"])

                logger.bind(tag=TAG).debug(
                    f"Speech recognition time: {time.time() - start_time:.3f}s | Result: {text}"
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
                logger.bind(tag=TAG).error(
                    f"Speech recognition failed: {e}", exc_info=True)
                return "", file_path

            finally:
                # File cleanup logic
                if self.delete_audio_file and file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.bind(tag=TAG).debug(
                            f"Deleted temporary audio file: {file_path}")
                    except Exception as e:
                        logger.bind(tag=TAG).error(
                            f"File deletion failed: {file_path} | Error: {e}"
                        )
