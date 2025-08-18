import time
import wave
import os
import sys
import io
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.dto.dto import InterfaceType
from core.providers.asr.base import ASRProviderBase

import numpy as np
import sherpa_onnx

from modelscope.hub.file_download import model_file_download
try:
    from huggingface_hub import hf_hub_download
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

import requests
import tarfile
import urllib.request

TAG = __name__
logger = setup_logging()


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
        self.interface_type = InterfaceType.LOCAL
        self.model_dir = config.get("model_dir")
        self.output_dir = config.get("output_dir")
        self.model_type = config.get(
            "model_type", "sense_voice")  # Support paraformer
        self.delete_audio_file = delete_audio_file

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize model file paths based on model type
        model_files = self._get_model_files_for_type()

        # Download and check model files
        try:
            # Determine model source and ID based on model directory name
            model_info = self._get_model_id_from_dir()
            
            # Check if we need to download the entire model from GitHub
            if model_info["source"] == "github":
                # For GitHub models, check if any files are missing and download the whole archive
                missing_files = [f for f in model_files.values() if not os.path.isfile(f)]
                if missing_files:
                    logger.bind(tag=TAG).info("Downloading complete model from GitHub...")
                    self._download_from_github(model_info["url"], self.model_dir)
            else:
                # For individual file downloads (HuggingFace/ModelScope)
                for file_name, file_path in model_files.items():
                    if not os.path.isfile(file_path):
                        logger.bind(tag=TAG).info(
                            f"Downloading model file: {file_name}")
                        
                        if model_info["source"] == "huggingface" and HF_AVAILABLE:
                            # Use Hugging Face Hub
                            try:
                                hf_hub_download(
                                    repo_id=model_info["model_id"],
                                    filename=file_name,
                                    local_dir=self.model_dir,
                                    local_dir_use_symlinks=False
                                )
                            except Exception as e:
                                logger.bind(tag=TAG).warning(
                                    f"HuggingFace download failed: {e}, trying ModelScope...")
                                # Fallback to ModelScope
                                model_file_download(
                                    model_id=model_info["model_id"],
                                    file_path=file_name,
                                    local_dir=self.model_dir,
                                )
                        else:
                            # Use ModelScope
                            model_file_download(
                                model_id=model_info["model_id"],
                                file_path=file_name,
                                local_dir=self.model_dir,
                            )

            # Verify all files exist after download
            for file_name, file_path in model_files.items():
                if not os.path.isfile(file_path):
                    raise FileNotFoundError(
                        f"Model file not found after download: {file_path}")

            # Set model paths based on type
            if self.model_type == "whisper":
                self.encoder_path = list(model_files.values())[0]  # encoder
                self.decoder_path = list(model_files.values())[1]  # decoder  
                self.tokens_path = list(model_files.values())[2]   # tokens
            elif self.model_type == "zipformer":
                # Handle different zipformer file naming patterns
                model_name = os.path.basename(self.model_dir)
                if "gigaspeech" in model_name:
                    self.encoder_path = model_files["encoder-epoch-30-avg-1.onnx"]
                    self.decoder_path = model_files["decoder-epoch-30-avg-1.onnx"]
                    self.joiner_path = model_files["joiner-epoch-30-avg-1.onnx"]
                else:
                    self.encoder_path = model_files["encoder-epoch-99-avg-1.onnx"]
                    self.decoder_path = model_files["decoder-epoch-99-avg-1.onnx"]
                    self.joiner_path = model_files["joiner-epoch-99-avg-1.onnx"]
                self.tokens_path = model_files["tokens.txt"]
            else:
                self.model_path = model_files["model.int8.onnx"]
                self.tokens_path = model_files["tokens.txt"]

        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Model file processing failed: {str(e)}")
            raise

        # Initialize the model
        self._initialize_model()

    def _get_model_id_from_dir(self) -> str:
        """Determine ModelScope model ID based on model directory name"""
        dir_name = os.path.basename(self.model_dir)
        
        # Map directory names to model sources (ModelScope and HuggingFace)
        model_mapping = {
            # Multilingual models
            "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17": {
                "source": "modelscope",
                "model_id": "pengzhendong/sherpa-onnx-sense-voice-zh-en-ja-ko-yue"
            },
            
            # English-only Whisper models (HuggingFace - more reliable)
            "sherpa-onnx-whisper-tiny.en": {
                "source": "huggingface",
                "model_id": "csukuangfj/sherpa-onnx-whisper-tiny.en"
            },
            "sherpa-onnx-whisper-base.en": {
                "source": "huggingface", 
                "model_id": "csukuangfj/sherpa-onnx-whisper-base.en"
            },
            "sherpa-onnx-whisper-small.en": {
                "source": "huggingface",
                "model_id": "csukuangfj/sherpa-onnx-whisper-small.en"
            },
            "sherpa-onnx-whisper-medium.en": {
                "source": "huggingface",
                "model_id": "csukuangfj/sherpa-onnx-whisper-medium.en"
            },
            
            # English-only Zipformer models (HuggingFace)
            "sherpa-onnx-zipformer-en-2023-04-01": {
                "source": "huggingface",
                "model_id": "csukuangfj/sherpa-onnx-zipformer-en-2023-04-01"
            },
            "sherpa-onnx-zipformer-gigaspeech-2023-12-12": {
                "source": "github",
                "model_id": "sherpa-onnx-zipformer-gigaspeech-2023-12-12",
                "url": "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-zipformer-gigaspeech-2023-12-12.tar.bz2"
            },
        }
        
        return model_mapping.get(dir_name, {
            "source": "modelscope",
            "model_id": "pengzhendong/sherpa-onnx-sense-voice-zh-en-ja-ko-yue"
        })

    def _get_model_files_for_type(self) -> dict:
        """Get required model files based on model type"""
        if self.model_type == "whisper":
            # Dynamic file names based on model directory
            model_name = os.path.basename(self.model_dir)
            if "tiny.en" in model_name:
                prefix = "tiny.en"
            elif "base.en" in model_name:
                prefix = "base.en"
            elif "small.en" in model_name:
                prefix = "small.en"
            elif "medium.en" in model_name:
                prefix = "medium.en"
            else:
                prefix = "tiny.en"  # default
                
            return {
                f"{prefix}-encoder.onnx": os.path.join(self.model_dir, f"{prefix}-encoder.onnx"),
                f"{prefix}-decoder.onnx": os.path.join(self.model_dir, f"{prefix}-decoder.onnx"),
                f"{prefix}-tokens.txt": os.path.join(self.model_dir, f"{prefix}-tokens.txt"),
            }
        elif self.model_type == "zipformer":
            # Check for different zipformer file naming patterns
            model_name = os.path.basename(self.model_dir)
            if "gigaspeech" in model_name:
                return {
                    "encoder-epoch-30-avg-1.onnx": os.path.join(self.model_dir, "encoder-epoch-30-avg-1.onnx"),
                    "decoder-epoch-30-avg-1.onnx": os.path.join(self.model_dir, "decoder-epoch-30-avg-1.onnx"),
                    "joiner-epoch-30-avg-1.onnx": os.path.join(self.model_dir, "joiner-epoch-30-avg-1.onnx"),
                    "tokens.txt": os.path.join(self.model_dir, "tokens.txt"),
                }
            else:
                return {
                    "encoder-epoch-99-avg-1.onnx": os.path.join(self.model_dir, "encoder-epoch-99-avg-1.onnx"),
                    "decoder-epoch-99-avg-1.onnx": os.path.join(self.model_dir, "decoder-epoch-99-avg-1.onnx"),
                    "joiner-epoch-99-avg-1.onnx": os.path.join(self.model_dir, "joiner-epoch-99-avg-1.onnx"),
                    "tokens.txt": os.path.join(self.model_dir, "tokens.txt"),
                }
        else:  # sense_voice or paraformer
            return {
                "model.int8.onnx": os.path.join(self.model_dir, "model.int8.onnx"),
                "tokens.txt": os.path.join(self.model_dir, "tokens.txt"),
            }

    def _download_from_github(self, url: str, model_dir: str):
        """Download and extract model from GitHub releases"""
        try:
            # Create parent directory
            parent_dir = os.path.dirname(model_dir)
            os.makedirs(parent_dir, exist_ok=True)
            
            # Download the tar.bz2 file to a temporary location
            tar_filename = os.path.join(parent_dir, "temp_model.tar.bz2")
            logger.bind(tag=TAG).info(f"Downloading from GitHub: {url}")
            
            urllib.request.urlretrieve(url, tar_filename)
            
            # Extract the tar.bz2 file
            logger.bind(tag=TAG).info("Extracting model files...")
            with tarfile.open(tar_filename, 'r:bz2') as tar:
                # Extract to parent directory
                tar.extractall(parent_dir)
            
            # Clean up the tar file
            os.remove(tar_filename)
            
            # Verify the extracted directory exists
            if os.path.exists(model_dir):
                logger.bind(tag=TAG).info("GitHub model download completed successfully")
            else:
                raise FileNotFoundError(f"Extracted model directory not found: {model_dir}")
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"GitHub download failed: {e}")
            raise

    def _initialize_model(self):
        """Initialize the appropriate model based on type"""
        with CaptureOutput():
            if self.model_type == "paraformer":
                self.model = sherpa_onnx.OfflineRecognizer.from_paraformer(
                    paraformer=self.model_path,
                    tokens=self.tokens_path,
                    num_threads=2,
                    decoding_method="greedy_search",
                    debug=False,
                )
            elif self.model_type == "whisper":
                self.model = sherpa_onnx.OfflineRecognizer.from_whisper(
                    encoder=self.encoder_path,
                    decoder=self.decoder_path,
                    tokens=self.tokens_path,
                    num_threads=2,
                    decoding_method="greedy_search",
                    debug=False,
                )
            elif self.model_type == "zipformer":
                self.model = sherpa_onnx.OfflineRecognizer.from_transducer(
                    encoder=self.encoder_path,
                    decoder=self.decoder_path,
                    joiner=self.joiner_path,
                    tokens=self.tokens_path,
                    num_threads=2,
                    decoding_method="greedy_search",
                    debug=False,
                )
            else:  # sense_voice
                self.model = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                    model=self.model_path,
                    tokens=self.tokens_path,
                    num_threads=2,
                    decoding_method="greedy_search",
                    debug=False,
                    use_itn=True,
                )

    def read_wave(self, wave_filename: str) -> Tuple[np.ndarray, int]:
        """
        Args:
        wave_filename:
            Path to a wave file. It should be single channel and each sample should
            be 16-bit. Its sample rate does not need to be 16kHz.
        Returns:
        Return a tuple containing:
        - A 1-D array of dtype np.float32 containing the samples, which are
        normalized to the range [-1, 1].
        - sample rate of the wave file
        """

        with wave.open(wave_filename) as f:
            assert f.getnchannels() == 1, f.getnchannels()
            assert f.getsampwidth() == 2, f.getsampwidth()  # it is in bytes
            num_samples = f.getnframes()
            samples = f.readframes(num_samples)
            samples_int16 = np.frombuffer(samples, dtype=np.int16)
            samples_float32 = samples_int16.astype(np.float32)

            samples_float32 = samples_float32 / 32768
            return samples_float32, f.getframerate()

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Main processing logic for speech to text"""
        file_path = None
        try:
            # Save audio file
            start_time = time.time()
            if audio_format == "pcm":
                pcm_data = opus_data
            else:
                pcm_data = self.decode_opus(opus_data)
            file_path = self.save_audio_to_file(pcm_data, session_id)
            logger.bind(tag=TAG).debug(
                f"Audio file save time: {time.time() - start_time:.3f}s | Path: {file_path}"
            )

            # Speech recognition
            start_time = time.time()
            s = self.model.create_stream()
            samples, sample_rate = self.read_wave(file_path)
            s.accept_waveform(sample_rate, samples)
            self.model.decode_stream(s)
            text = s.result.text
            logger.bind(tag=TAG).debug(
                f"Speech recognition time: {time.time() - start_time:.3f}s | Result: {text}"
            )

            # Calculate audio length from WAV file
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                audio_length_seconds = frames / float(rate)

            # Log the transcript information - TEMPORARILY DISABLED
            # self.log_audio_transcript(file_path, audio_length_seconds, text)

            return text, file_path

        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Speech recognition failed: {e}", exc_info=True)
            return "", file_path
        finally:
            # File cleanup logic - DISABLED to preserve audio files
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                logger.bind(tag=TAG).info(
                    f"Audio file preserved (deletion disabled): {file_path}")
                # Commented out deletion code to preserve audio files
                try:
                    os.remove(file_path)
                    logger.bind(tag=TAG).debug(
                        f"Deleted temporary audio file: {file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"File deletion failed: {file_path} | Error: {e}")
