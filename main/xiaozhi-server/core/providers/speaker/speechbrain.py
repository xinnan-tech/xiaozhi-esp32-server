import os
import time
import torch
import pyaudio
import numpy as np
from collections import deque
from scipy.io import wavfile
from scipy.spatial.distance import cosine
from speechbrain.pretrained import SpeakerRecognition

from core.providers.speaker.base import SpeakerProviderBase
from typing import Optional, Tuple, List

import wave
import uuid

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# 音频参数
SAMPLE_RATE = 16000
CHUNK = 1024
CHANNELS = 1
FORMAT = pyaudio.paInt16
BUFFER_SECONDS = 2
THRESHOLD = 0.35
ENROLL_FILE = "enrolled_voice.wav"



class SpeechBrainProvider(SpeakerProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        self.delete_audio_file = delete_audio_file

        # 初始化模型
        print("🔁 正在加载说话人识别模型...")
        self.model = SpeakerRecognition.from_hparams(source="speechbrain/spkrec-ecapa-voxceleb")
        print("✅ 模型加载完成")

    def load_audio_embedding(self,filepath):
        wav_tensor = self.model.load_audio(filepath).unsqueeze(0)
        embed = self.model.encode_batch(wav_tensor).squeeze().detach().cpu().numpy()
        return embed

    def verify_from_array(self,audio_array: np.ndarray):
        global owner_embed
        print("🔁 正在加载owner_embed...")
        owner_embed = self.load_audio_embedding(ENROLL_FILE)
        if audio_array.dtype != np.float32:
            audio_array = audio_array.astype(np.float32)

        audio_tensor = torch.from_numpy(audio_array).unsqueeze(0)
        embed = self.model.encode_batch(audio_tensor).squeeze().detach().cpu().numpy()
        score = 1 - cosine(owner_embed, embed)
        return score

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """PCM数据保存为WAV文件"""
        module_name = __name__.split(".")[-1]
        file_name = f"speaker_{module_name}_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    def verify_voice(
        self, file_path: str,audio_data: List[bytes], session_id: str
    ) -> Tuple[Optional[bool], Optional[float]]:
        """验证说话人处理逻辑"""

        # 使用 SpeechBrain 模型对比
        score, prediction = self.model.verify_files(ENROLL_FILE, file_path)
        # os.remove(temp_file)

        print(f"[识别结果] 相似度分数：{score.item():.4f}")
        if prediction:
            print("✅ 说话人身份通过（与注册声音一致）")
            return prediction,score
        else:
            print("❌ 说话人身份不一致")
            return False,-1.0



