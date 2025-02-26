import os
import uuid
import json
import base64
import requests # type: ignore
import argparse
import logging
import torch # type: ignore
import torchaudio # type: ignore
import numpy as np # type: ignore
from datetime import datetime
from core.providers.tts.base import TTSProviderBase



class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        url = "http:// ip:port /inference_zero_shot" # CosyVoice的FastAPI 服务地址和接口
        payload = {
            'tts_text': text,
            'prompt_text': '希望你以后能够做的比我还好呦。' # 参考音频的文本
        }
        files = [('prompt_wav', ('prompt_wav', open('./asset/zero_shot_prompt.wav', 'rb'), 'application/octet-stream'))] # asset/zero_shot_prompt.wav 是放根目录的参考音频修改声音的
        response = requests.request("GET", url, data=payload, files=files, stream=True)
        tts_audio = b''
        for r in response.iter_content(chunk_size=16000):
            tts_audio += r
        tts_speech = torch.from_numpy(np.array(np.frombuffer(tts_audio, dtype=np.int16))).unsqueeze(dim=0)
        torchaudio.save(output_file, tts_speech, 22050)
