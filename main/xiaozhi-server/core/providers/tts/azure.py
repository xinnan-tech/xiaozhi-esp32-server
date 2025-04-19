import os
import asyncio
import aiohttp
import time
from .base import TTSProviderBase

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.subscription_key = config.get("subscription_key")
        self.region = config.get("region", "eastus")
        self.voice_name = config.get("voice_name", "zh-CN-YunxiNeural")
        self.output_format = config.get("output_format", "audio-24khz-48kbitrate-mono-mp3")
        self.api_url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"
        self.token_url = f"https://{self.region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        self.access_token = None
        self.token_expiry = 0
        
    def generate_filename(self, extension=".wav"):
        """生成唯一的音频文件名"""
        return os.path.join(self.output_file, f"azure_tts_{os.urandom(4).hex()}{extension}")

    async def _get_access_token(self):
        """获取Azure TTS访问令牌"""
        if time.time() < self.token_expiry and self.access_token:
            return self.access_token
            
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.token_url,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        self.access_token = await response.text()
                        self.token_expiry = time.time() + 540  # 令牌有效期9分钟(540秒)
                        return self.access_token
                    else:
                        error = await response.text()
                        raise Exception(f"获取Azure TTS令牌失败: {response.status} - {error}")
        except Exception as e:
            raise Exception(f"获取Azure TTS令牌异常: {e}")

    async def text_to_speak(self, text, output_file):
        """调用Azure TTS API将文本转换为语音"""
        token = await self._get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": self.output_format,
            "User-Agent": "xiaozhi-server"
        }
        
        ssml = f"""<speak version='1.0' xml:lang='zh-CN'>
            <voice name='{self.voice_name}'>
                {text}
            </voice>
        </speak>"""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    data=ssml.encode("utf-8")
                ) as response:
                    if response.status == 200:
                        with open(output_file, "wb") as f:
                            f.write(await response.read())
                    else:
                        error = await response.text()
                        headers = response.headers
                        raise Exception(f"Azure TTS请求失败: {response.status} - 错误信息: {error}, 完整响应: {response}")
        except Exception as e:
            raise Exception(f"Azure TTS请求异常: {e}")
