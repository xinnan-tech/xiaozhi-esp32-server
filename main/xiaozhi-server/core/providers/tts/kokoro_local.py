import os
import base64
import uuid
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
import torch
from pathlib import Path
import numpy as np
import soundfile as sf
from kokoro import KModel, KPipeline


REPO_ID = 'hexgrad/Kokoro-82M-v1.1-zh'
SAMPLE_RATE = 24000

# HACK: Mitigate rushing caused by lack of training data beyond ~100 tokens
# Simple piecewise linear fn that decreases speed as len_ps increases
@staticmethod
def _speed_callable(len_ps):
    speed = 0.8
    if len_ps <= 83:
        speed = 1
    elif len_ps < 183:
        speed = 1 - (len_ps - 83) / 500
    return speed * 1.3
    
class TTSProvider(TTSProviderBase):
    
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.appid = config.get("appid")
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = 'mps' if torch.backends.mps.is_available() else 'cpu'
        self.model_dir = config.get("model_dir")
        
        self.en_pipeline = KPipeline(lang_code='a', repo_id=REPO_ID, model=False)
        model = KModel(repo_id=REPO_ID, 
                       config=f"{self.model_dir}/config.json", 
                       model=f"{self.model_dir}/kokoro-v1_1-zh.pth", 
                       disable_complex=True).to(self.device).eval()
        self.zh_pipeline = KPipeline(lang_code='z', repo_id=REPO_ID, model=model, en_callable=self.en_callable)
        self.voice = f"{self.model_dir}/voices/{config.get('voice')}.pt"
        
    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        try:
            generator = self.zh_pipeline(text, voice=self.voice, speed=_speed_callable)
            result = next(generator)
            wav = result.audio
            # 调整音量，乘以一个因子（例如 0.5 表示减小音量，2.0 表示增大音量）
            volume_factor = 1.5
            wav = wav * volume_factor
            sf.write(output_file, wav, SAMPLE_RATE)
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")


    def en_callable(self, text):
        return next(self.en_pipeline(text)).phonemes


     