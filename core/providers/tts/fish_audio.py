import os
import uuid
import ormsgpack
import httpx
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, conint
from typing import Annotated
from core.providers.tts.base import TTSProviderBase

class ServeReferenceAudio(BaseModel):
    audio: bytes
    text: str

class ServeTTSRequest(BaseModel):
    text: str
    chunk_length: Annotated[int, conint(ge=100, le=300, strict=True)] = 200
    format: Literal["wav", "pcm", "mp3"] = "mp3"
    mp3_bitrate: Literal[64, 128, 192] = 128
    references: list[ServeReferenceAudio] = []
    reference_id: str | None = None
    normalize: bool = True
    latency: Literal["normal", "balanced"] = "normal"

class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.api_key = config.get("api_key")
        self.api_url = config.get("api_url")
        self.voice = config.get("voice")
        self.output_file = config.get("output_file")

    def generate_filename(self, extension=".mp3"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        request = ServeTTSRequest(
            text=text,
            references=[],  # 如果需要参考音频可以在这里添加
            reference_id=self.voice  # 使用配置的voice作为reference_id
        )
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                self.api_url,
                content=ormsgpack.packb(request, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/msgpack",
                },
                timeout=None,
            ) as response:
                if response.status_code == 200:
                    with open(output_file, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            f.write(chunk)
                else:
                    raise ValueError(f"TTS请求失败: {response.status_code} - {response.text}")
