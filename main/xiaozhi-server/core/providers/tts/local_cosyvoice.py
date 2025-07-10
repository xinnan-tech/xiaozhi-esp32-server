import os
import sys
import uuid
import requests
from config.logger import get_logger
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
import torch
import torchaudio

TAG = __name__
logger = get_logger(TAG)


class TTSProvider(TTSProviderBase):

    def _initialize_model(self):
        # 保存原始 sys.path
        original_path = None

        try:
            original_path = sys.path.copy()
            # 动态修改 sys.path
            sys.path.insert(0, self.matcha_tts_path)
            sys.path.insert(0, self.cosy_voice_path)

            # 导入必要的模块
            from cosyvoice.cli.cosyvoice import CosyVoice2
            from cosyvoice.utils.file_utils import load_wav

            # 初始化模型
            self.model = CosyVoice2(self.cosy_voice_model_dir,
                                    load_jit=False, load_trt=False, fp16=False)

            # 保存导入的模块供之后使用
            self.CosyVoice2 = CosyVoice2
            self.prompt_speech_16k = load_wav(self.prompt_speech_16k, 16000)

            return True
        except ImportError as e:
            logger.bind(tag=TAG).error(f"导入 CosyVoice 模块失败: {e}")
            raise ImportError(f"导入 CosyVoice 模块失败: {e}")
        finally:
            # 恢复原始 sys.path
            if original_path:
                sys.path = original_path

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.cosy_voice_path = config.get("cosyvoice_path")
        self.cosy_voice_model_dir = config.get("cosyvoice_model_dir")
        self.matcha_tts_path = config.get("matcha_tts_path") if config.get(
            "matcha_tts_path") else f"{self.cosy_voice_path}/third_party/Matcha-TTS"

        self.prompt_speech_16k = config.get("prompt_speech_16k") if config.get(
            "prompt_speech_16k") else f"{self.cosy_voice_path}/asset/zero_shot_prompt.wav"
        # 非必传参数，如果不传，则使用默认的16k采样率的提示音频
        self.prompt_speech_16k_text = config.get("prompt_speech_16k_text") if config.get(
            "prompt_speech_16k_text") else None

        self._initialize_model()

    def inference_to_single_file(self, inference_func, output_path, *args, **kwargs):
        """
        执行推理并将结果保存为单个音频文件

        参数:
            inference_func: 推理函数(如cosyvoice.inference_zero_shot)
            output_path: 输出文件路径
            *args, **kwargs: 传递给推理函数的参数

        返回:
            合并后的语音张量
        """
        speech_segments = []
        for segment in inference_func(*args, **kwargs):
            speech_segments.append(segment['tts_speech'])
        if speech_segments:
            combined_speech = torch.cat(speech_segments, dim=1)
            torchaudio.save(output_path, combined_speech, self.model.sample_rate)
            return combined_speech
        return None

    def generate_filename(self):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}.{self.format}")

    async def text_to_speak(self, text, output_file):
        try:
            if not self.prompt_speech_16k_text:
                self.inference_to_single_file(
                    self.model.inference_cross_lingual,
                    output_file,
                    text,
                    self.prompt_speech_16k,
                    stream=False
                )
            else:
                self.inference_to_single_file(
                    self.model.inference_zero_shot,
                    output_file,
                    text,
                    self.prompt_speech_16k_text,
                    self.prompt_speech_16k,
                    stream=False
                )
        except Exception as e:
            logger.bind(tag=TAG).exception(f"CosyVoice TTS请求失败: {e}")