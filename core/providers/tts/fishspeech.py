import base64
import os
import traceback
import uuid
import queue
import io

import numpy as np
import requests
import ormsgpack
from pathlib import Path

import torch
import torchaudio
from pydantic import BaseModel, Field, conint, model_validator
from pydub import AudioSegment
from typing_extensions import Annotated
from datetime import datetime
from typing import Literal
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class ServeReferenceAudio(BaseModel):
    audio: bytes
    text: str

    @model_validator(mode="before")
    def decode_audio(cls, values):
        audio = values.get("audio")
        if (
                isinstance(audio, str) and len(audio) > 255
        ):  # Check if audio is a string (Base64)
            try:
                values["audio"] = base64.b64decode(audio)
            except Exception as e:
                # If the audio is not a valid base64 string, we will just ignore it and let the server handle it
                pass
        return values

    def __repr__(self) -> str:
        return f"ServeReferenceAudio(text={self.text!r}, audio_size={len(self.audio)})"


class ServeTTSRequest(BaseModel):
    text: str
    chunk_length: Annotated[int, conint(ge=100, le=300, strict=True)] = 200
    # Audio format
    format: Literal["wav", "pcm", "mp3"] = "wav"
    # References audios for in-context learning
    references: list[ServeReferenceAudio] = []
    # Reference id
    # For example, if you want use https://fish.audio/m/7f92f8afb8ec43bf81429cc1c9199cb1/
    # Just pass 7f92f8afb8ec43bf81429cc1c9199cb1
    reference_id: str | None = None
    seed: int | None = None
    use_memory_cache: Literal["on", "off"] = "off"
    # Normalize text for en & zh, this increase stability for numbers
    normalize: bool = True
    # not usually used below
    streaming: bool = False
    max_new_tokens: int = 1024
    top_p: Annotated[float, Field(ge=0.1, le=1.0, strict=True)] = 0.7
    repetition_penalty: Annotated[float, Field(ge=0.9, le=2.0, strict=True)] = 1.2
    temperature: Annotated[float, Field(ge=0.1, le=1.0, strict=True)] = 0.7

    class Config:
        # Allow arbitrary types for pytorch related types
        arbitrary_types_allowed = True


def audio_to_bytes(file_path):
    if not file_path or not Path(file_path).exists():
        return None
    with open(file_path, "rb") as wav_file:
        wav = wav_file.read()
    return wav


def read_ref_text(ref_text):
    path = Path(ref_text)
    if path.exists() and path.is_file():
        with path.open("r", encoding="utf-8") as file:
            return file.read()
    return ref_text


class TTSProvider(TTSProviderBase):

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)

        self.reference_id = config.get("reference_id")
        self.reference_audio = config.get("reference_audio", [])
        self.reference_text = config.get("reference_text", [])
        self.format = config.get("format", "wav")
        self.channels = config.get("channels", 1)
        self.rate = config.get("rate", 44100)
        self.api_key = config.get("api_key", "YOUR_API_KEY")
        if "你" in self.api_key:
            logger.bind(tag=TAG).error("你还没配置FishSpeech TTS的密钥，请在配置文件中配置密钥，否则无法正常工作")
            return
        self.normalize = config.get("normalize", True)
        self.max_new_tokens = config.get("max_new_tokens", 1024)
        self.chunk_length = config.get("chunk_length", 200)
        self.top_p = config.get("top_p", 0.7)
        self.repetition_penalty = config.get("repetition_penalty", 1.2)
        self.temperature = config.get("temperature", 0.7)
        self.streaming = config.get("streaming", False)
        self.use_memory_cache = config.get("use_memory_cache", "on")
        self.seed = config.get("seed")
        self.api_url = config.get("api_url", "http://127.0.0.1:8080/v1/tts")

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        # Prepare reference data
        byte_audios = [audio_to_bytes(ref_audio) for ref_audio in self.reference_audio]
        ref_texts = [read_ref_text(ref_text) for ref_text in self.reference_text]

        data = {
            "text": text,
            "references": [
                ServeReferenceAudio(
                    audio=audio if audio else b"", text=text
                )
                for text, audio in zip(ref_texts, byte_audios)
            ],
            "reference_id": self.reference_id,
            "normalize": self.normalize,
            "format": self.format,
            "max_new_tokens": self.max_new_tokens,
            "chunk_length": self.chunk_length,
            "top_p": self.top_p,
            "repetition_penalty": self.repetition_penalty,
            "temperature": self.temperature,
            "streaming": self.streaming,
            "use_memory_cache": self.use_memory_cache,
            "seed": self.seed,
        }

        pydantic_data = ServeTTSRequest(**data)

        response = requests.post(
            self.api_url,
            data=ormsgpack.packb(pydantic_data, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/msgpack",
            },
        )

        if response.status_code == 200:
            audio_content = response.content

            with open(output_file, "wb") as audio_file:
                audio_file.write(audio_content)



        else:
            print(f"Request failed with status code {response.status_code}")
            print(response.json())

    def _get_audio_from_tts(self, data_bytes):
        tts_speech = torch.from_numpy(np.array(np.frombuffer(data_bytes, dtype=np.int16))).unsqueeze(dim=0)
        with io.BytesIO() as bf:
            torchaudio.save(bf, tts_speech, 44100, format="wav")
            audio = AudioSegment.from_file(bf, format="wav")
        audio = audio.set_channels(1).set_frame_rate(16000)
        return audio

    async def text_to_speak_stream(self, text, queue: queue.Queue, text_index=0):
        try:
            # Prepare reference data
            byte_audios = [audio_to_bytes(ref_audio) for ref_audio in self.reference_audio]
            ref_texts = [read_ref_text(ref_text) for ref_text in self.reference_text]

            data = {
                "text": text,
                "references": [
                    ServeReferenceAudio(
                        audio=audio if audio else b"", text=text
                    )
                    for text, audio in zip(ref_texts, byte_audios)
                ],
                "reference_id": self.reference_id,
                "normalize": self.normalize,
                "format": self.format,
                "max_new_tokens": self.max_new_tokens,
                "chunk_length": self.chunk_length,
                "top_p": self.top_p,
                "repetition_penalty": self.repetition_penalty,
                "temperature": self.temperature,
                "streaming": self.streaming,
                "use_memory_cache": self.use_memory_cache,
                "seed": self.seed,
            }

            pydantic_data = ServeTTSRequest(**data)
            audio_buff = None
            chunk_total = b''
            last_raw = b''
            audio_raw = b''
            print("请求tts")
            with requests.post(
                    self.api_url,
                    data=ormsgpack.packb(pydantic_data, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/msgpack",
                    },
            ) as response:
                if response.status_code == 200:
                    for chunk in response.iter_content():
                        # 拼接当前块和上一块数据
                        chunk_total += chunk
                        # 最后一个是静音，说明是一个完整的音频
                        if len(chunk_total) % 2 == 0 and chunk_total[-2:] == b'\x00\x00':
                            audio = self._get_audio_from_tts(chunk_total)
                            audio_raw = audio_raw + audio.raw_data
                            #长度凑够2贞开始发送，60ms*4=240ms
                            if len(audio_raw) >= 7680:
                                duration = 60 * len(audio_raw) // 1920
                                if (len(audio_raw) % 1920) > 0:
                                    duration += 60
                                duration = duration / 1000.0
                                logger.bind(tag=TAG).info(f'发送数据长度：{len(audio_raw)}')
                                opus_datas = self.wav_to_opus_data_audio_raw(audio_raw)
                                queue.put({
                                    "data": opus_datas,
                                    "duration": duration,
                                    "end": False,
                                    "text_index": text_index
                                })
                                audio_raw = b''
                            chunk_total = b''
                    if len(chunk_total) > 0:
                        audio = self._get_audio_from_tts(chunk_total)
                        audio_raw = audio_raw + audio.raw_data
                        duration = 60 * len(audio_raw) // 1920
                        if (len(audio_raw) % 1920) > 0:
                            duration += 60
                        duration = duration / 1000.0
                        # 把 audio 转成 opus
                        logger.bind(tag=TAG).info(f'发送数据长度：{len(audio_raw)}')
                        opus_datas = self.wav_to_opus_data_audio_raw(audio_raw)
                        queue.put({
                            "data": opus_datas,
                            "duration": duration,
                            "end": False
                        })

                else:
                    print('请求失败:', response.status_code, response.text)
                queue.put({
                    "data": None,
                    "end": True
                })
        except Exception as e:
            logger.bind(tag=TAG).error("tts发生错误")
            traceback.print_exc()
            raise e
