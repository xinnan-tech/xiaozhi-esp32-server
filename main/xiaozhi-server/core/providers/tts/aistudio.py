from functools import lru_cache
import os
import uuid
import json
import base64
import requests
from datetime import datetime
from core.providers.tts.base import TTSProviderBase
from urllib.parse import quote
import wave

@lru_cache
def gen_text_auto(text: str, tts_url: str, access_token: str, **kwargs) -> bytes:
    default_params = {
        "tex": text,
        "tok": access_token,
        "cuid": "yvON5IRqAdXhh6IFtZ5QF1nxbi4bv32Y",  # 默认 CUID
        "ctp": 1,  # 客户端类型
        "lan": "zh",  # 语言类型，中文
        "spd": 5,  # 语速
        "pit": 5,  # 音调
        "vol": 5,  # 音量
        "per": 1,  # 发音人
        "aue": 6  # 音频编码格式 wav
    }
    # 更新默认参数
    default_params.update(kwargs)

    # 特殊处理tex参数，需要进行两次URL编码
    # 先对tex参数进行一次URL编码（httpx会自动进行第二次编码）
    default_params["tex"] = quote(default_params["tex"])

    # 发送 POST 请求
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '*/*'
    }
    response = requests.post(tts_url, headers=headers, data=default_params)
    response.raise_for_status()  # 检查HTTP错误
    return response.content  # 返回音频内容

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.tts_url = "https://tsn.baidu.com/text2audio"
        self.token_url = "https://aip.baidubce.com/oauth/2.0/token"
        self.access_token = self.get_access_token(config.get("api_key"), config.get("secret_key"))

    def get_access_token(self, api_key: str, secret_key: str) -> str | None:
        """
        使用 AK，SK 生成鉴权签名（Access Token）
        :return: access_token，或是 None（如果错误）
        """
        params = {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": secret_key
        }
        try:
            response = requests.post(self.token_url, params=params, timeout=10)
            response.raise_for_status()  # 检查HTTP错误
            token_response = response.json()  # 直接解析为JSON字典
            return token_response.get("access_token")
        except requests.RequestException as e:
            print("Failed to get access token:", e)
            return None

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        if not text:
            raise ValueError("Text cannot be empty")
        if not self.access_token:
            raise ValueError("Access token is not available")

        try:
            resp = gen_text_auto(text, self.tts_url, self.access_token)
            if resp is not None and len(resp) > 0:
                with wave.open(output_file, 'wb') as wf:
                    wf.setnchannels(1) # Mono
                    wf.setsampwidth(2) # 16-bit PCM
                    wf.setframerate(16000) # rate
                    wf.writeframes(resp)
            else:
                raise Exception(f"{__name__} response is empty or invalid")
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")
