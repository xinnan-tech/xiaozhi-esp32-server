import time
import wave
import os
import sys
import io
from config.logger import setup_logging
from typing import Optional, Tuple, List
import uuid
import opuslib_next
from core.providers.asr.base import ASRProviderBase

import numpy as np
import sherpa_onnx

from modelscope.hub.file_download import model_file_download

TAG = __name__
logger = setup_logging()


# 捕获标准输出
class CaptureOutput:
    def __enter__(self):
        self._output = io.StringIO()
        self._original_stdout = sys.stdout
        sys.stdout = self._output

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self._original_stdout
        self.output = self._output.getvalue()
        self._output.close()

        # 将捕获到的内容通过 logger 输出
        if self.output:
            logger.bind(tag=TAG).info(self.output.strip())


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        self.model_dir = config.get("model_dir")
        self.output_dir = config.get("output_dir")
        self.delete_audio_file = delete_audio_file

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化模型文件路径
        model_files = {
            "model.int8.onnx": os.path.join(self.model_dir, "model.int8.onnx"),
            "tokens.txt": os.path.join(self.model_dir, "tokens.txt")
        }

        # 下载并检查模型文件
        try:
            for file_name, file_path in model_files.items():
                if not os.path.isfile(file_path):
                    logger.bind(tag=TAG).info(f"正在下载模型文件: {file_name}")
                    model_file_download(
                        model_id="pengzhendong/sherpa-onnx-sense-voice-zh-en-ja-ko-yue",
                        file_path=file_name,
                        local_dir=self.model_dir
                    )
                    
                    if not os.path.isfile(file_path):
                        raise FileNotFoundError(f"模型文件下载失败: {file_path}")
                        
            self.model_path = model_files["model.int8.onnx"]
            self.tokens_path = model_files["tokens.txt"]
            
        except Exception as e:
            logger.bind(tag=TAG).error(f"模型文件处理失败: {str(e)}")
            raise

        with CaptureOutput():
            self.model = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=self.model_path,
                tokens=self.tokens_path,
                num_threads=2,
                sample_rate=16000,
                feature_dim=80,
                decoding_method="greedy_search",
                debug=False,
                use_itn=True,
            )

    def save_audio_to_file(self, opus_data: List[bytes], session_id: str) -> str:
        """将Opus音频数据解码并保存为WAV文件"""
        file_name = f"asr_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
        pcm_data = []

        for opus_packet in opus_data:
            try:
                pcm_frame = decoder.decode(opus_packet, 960)  # 960 samples = 60ms
                pcm_data.append(pcm_frame)
            except opuslib_next.OpusError as e:
                logger.bind(tag=TAG).error(f"Opus解码错误: {e}", exc_info=True)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

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

    async def speech_to_text(self, opus_data: List[bytes], session_id: str) -> Tuple[Optional[str], Optional[str]]:
        """语音转文本主处理逻辑"""
        file_path = None
        try:
            # 保存音频文件
            start_time = time.time()
            file_path = self.save_audio_to_file(opus_data, session_id)
            logger.bind(tag=TAG).debug(f"音频文件保存耗时: {time.time() - start_time:.3f}s | 路径: {file_path}")

            # 语音识别
            start_time = time.time()
            s = self.model.create_stream()
            samples, sample_rate = self.read_wave(file_path)
            s.accept_waveform(sample_rate, samples)
            self.model.decode_stream(s)
            text = s.result.text
            logger.bind(tag=TAG).debug(f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {text}")

            return text, file_path

        except Exception as e:
            logger.bind(tag=TAG).error(f"语音识别失败: {e}", exc_info=True)
            return "", None

        finally:
            # 文件清理逻辑
            if self.delete_audio_file and file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.bind(tag=TAG).debug(f"已删除临时音频文件: {file_path}")
                except Exception as e:
                    logger.bind(tag=TAG).error(f"文件删除失败: {file_path} | 错误: {e}")
