import asyncio
import io
import logging
import os
import json
import queue
import threading
import time
import uuid
import base64
import wave
from datetime import datetime
import edge_tts
import numpy as np
import opuslib
import requests
import torch
import torchaudio
from ormsgpack import ormsgpack

from core.utils.util import read_config, get_project_dir
from pydub import AudioSegment
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from fish_speech.utils.file import read_ref_text, audio_to_bytes
from fish_speech.utils.schema import ServeTTSRequest, ServeReferenceAudio

logger = logging.getLogger(__name__)


class TTS(ABC):
    def __init__(self, config, delete_audio_file):
        self.delete_audio_file = delete_audio_file
        self.output_file = config.get("output_file")
        self.delete_audio_file = delete_audio_file
        self.executor = ThreadPoolExecutor(max_workers=10)

    @abstractmethod
    def generate_filename(self):
        pass

    def to_tts(self, text):
        tmp_file = self.generate_filename()
        try:
            max_repeat_time = 5
            while not os.path.exists(tmp_file) and max_repeat_time > 0:
                asyncio.run(self.text_to_speak(text, tmp_file))
                if not os.path.exists(tmp_file):
                    max_repeat_time = max_repeat_time - 1
                    logger.error(f"语音生成失败: {text}:{tmp_file}，再试{max_repeat_time}次")

            return tmp_file
        except Exception as e:
            logger.info(f"Failed to generate TTS file: {e}")
            return None

    def to_tts_stream_queue(self, text, chunk_queue: queue.Queue):
        asyncio.run(self.text_to_speak_queue(text, chunk_queue))

    @abstractmethod
    async def text_to_speak_queue(self, text, queue: queue.Queue):
        pass

    @abstractmethod
    async def text_to_speak(self, text, output_file):
        pass

    def wav_to_opus_data(self, wav_file_path):
        # 使用pydub加载PCM文件
        # 获取文件后缀名
        file_type = os.path.splitext(wav_file_path)[1]
        if file_type:
            file_type = file_type.lstrip('.')
        audio = AudioSegment.from_file(wav_file_path, format=file_type)

        return self.wav_to_opus_data_byte(audio)

    def wav_to_opus_data_audio(self, chunk, type_format="mp3"):
        print(f"长度：{len(chunk)}")
        tts_speech = torch.from_numpy(np.array(np.frombuffer(chunk, dtype=np.int16))).unsqueeze(dim=0)
        with io.BytesIO() as bf:
            torchaudio.save(bf, tts_speech, 44100, format="wav")
            audio = AudioSegment.from_file(bf, format="wav")
        audio.fade_in(1000).fade_out(1000)
        return self.wav_to_opus_data_byte(audio)

    def wav_to_opus_data_byte(self, audio):
        duration = len(audio) / 1000.0
        # 转换为单声道和16kHz采样率（确保与编码器匹配）
        audio = audio.set_channels(1).set_frame_rate(16000)
        # 获取原始PCM数据（16位小端）
        raw_data = audio.raw_data
        # 初始化Opus编码器
        encoder = opuslib.Encoder(16000, 1, opuslib.APPLICATION_AUDIO)
        # 编码参数
        frame_duration = 60  # 60ms per frame
        frame_size = int(16000 * frame_duration / 1000)  # 960 samples/frame
        opus_datas = []
        # 按帧处理所有音频数据（包括最后一帧可能补零）
        for i in range(0, len(raw_data), frame_size * 2):  # 16bit=2bytes/sample
            # 获取当前帧的二进制数据
            chunk = raw_data[i:i + frame_size * 2]

            # 如果最后一帧不足，补零
            if len(chunk) < frame_size * 2:
                chunk += b'\x00' * (frame_size * 2 - len(chunk))

            # 转换为numpy数组处理
            np_frame = np.frombuffer(chunk, dtype=np.int16)

            # 编码Opus数据
            opus_data = encoder.encode(np_frame.tobytes(), frame_size)
            opus_datas.append(opus_data)
        return opus_datas, duration


class EdgeTTS(TTS):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.voice = config.get("voice")

    def generate_filename(self, extension=".mp3"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        communicate = edge_tts.Communicate(text, voice=self.voice)  # Use your preferred voice
        await communicate.save(output_file)


class CosyVoice_TTS(TTS):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url")
        self.ref_text = config.get("ref_text")
        self.audio_ref = get_project_dir() + "/" + config.get("audio_ref")
        self.audio_ref_byte = open(get_project_dir() + "/" + config.get("audio_ref"), 'rb')

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak_queue(self, text, queue: queue.Queue):
        # Prepare the files and data dictionaries
        files = {
            'prompt_wav': open(self.audio_ref, 'rb')}

        data = {
            'tts_text': text,
            'prompt_text': self.ref_text
        }

        last_chunk = b''  # 用于存储最后16个长度的音频数据
        overlap = 1112
        with requests.post(self.url, files=files, data=data, stream=True) as response:
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=22048):
                    # 拼接当前块和上一块数据
                    current_audio = last_chunk + chunk
                    queue.put({
                        "data": current_audio,
                        "end": False
                    })
                    # 只保留当前块的最后16个字节
                    last_chunk = current_audio[-overlap:]  # 这里可以根据实际音频样本长度调整
            else:
                print('请求失败:', response.status_code, response.text)
        queue.put({
            "data": None,
            "end": True
        })

    async def text_to_speak(self, text, output_file):
        raise "不支持"


class GPT_SoVits_TTS(TTS):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url")
        self.speaker_name = config.get("speaker_name")

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak_queue(self, text, queue: queue.Queue):
        resp = await self.requests_f(text)
        # 检查返回状态码
        if resp.status_code == 200:
            # 将音频流写入文件
            for chunk in resp.iter_content(chunk_size=8192):  # 分块写入
                queue.put({
                    "data": chunk,
                    "end": False
                })
        queue.put({
            "data": None,
            "end": True
        })

    async def text_to_speak(self, text, output_file):
        resp = await self.requests_f(text)
        # 检查返回状态码
        if resp.status_code == 200:
            # 将音频流写入文件
            with open(output_file, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):  # 分块写入
                    f.write(chunk)
            print('音频已保存为 output.wav')
        else:
            print(f"请求失败，状态码: {resp.status_code}")

    async def requests_f(self, text):
        request_json = {
            "text": text,
            "text_lang": "auto",
            "ref_id": self.speaker_name,
            "top_k": 5,
            "top_p": 1,
            "temperature": 1,
            "text_split_method": "cut5",
            "batch_size": 4,
            "batch_threshold": 0.75,
            "split_bucket": True,
            "speed_factor": 1.0,
            "fragment_interval": 0.2,
            "media_type": "wav",
            "streaming_mode": False,
            "parallel_infer": True,
            "repetition_penalty": 1.35
        }
        resp = requests.post(self.url, json.dumps(request_json))
        return resp


class FishSpeech_TTS(TTS):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url")
        self.ref_audios = [get_project_dir() + "/" + ref_audio for ref_audio in config.get("ref_audios")]
        self.ref_texts = config.get("ref_texts")
        self.normalize = config.get("normalize")
        self.api_key = config.get("api_key")
        self.format = config.get("format")
        self.max_new_tokens = config.get("max_new_tokens")
        self.chunk_length = config.get("chunk_length")
        self.top_p = config.get("top_p")
        self.repetition_penalty = config.get("repetition_penalty")
        self.temperature = config.get("temperature")
        self.streaming = config.get("streaming")
        self.use_memory_cache = config.get("use_memory_cache")
        self.seed = config.get("seed")

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak_queue(self, text, queue: queue.Queue):

        idstr = None
        # priority: ref_id > [{text, audio},...]
        if idstr is None:
            ref_audios = self.ref_audios
            ref_texts = self.ref_texts
            if ref_audios is None:
                byte_audios = []
            else:
                byte_audios = [audio_to_bytes(ref_audio) for ref_audio in ref_audios]
            if ref_texts is None:
                ref_texts = []
            else:
                ref_texts = [read_ref_text(ref_text) for ref_text in ref_texts]
        else:
            byte_audios = []
            ref_texts = []
            pass  # in api.py

        data = {
            "text": text,
            "references": [
                ServeReferenceAudio(
                    audio=ref_audio if ref_audio is not None else b"", text=ref_text
                )
                for ref_text, ref_audio in zip(ref_texts, byte_audios)
            ],
            "reference_id": idstr,
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
        last_chunk = b''
        overlap = 882
        chunk_total = b''
        with requests.post(
                self.url,
                data=ormsgpack.packb(pydantic_data, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
                stream=self.streaming,
                headers={
                    "authorization": f"Bearer {self.api_key}",
                    "content-type": "application/msgpack",
                },
        ) as response:
            if response.status_code == 200:
                for chunk in response.iter_content(chunk_size=52920):
                    # 拼接当前块和上一块数据
                    chunk_total += chunk
                    if len(chunk_total) >= 52920 and len(chunk_total)%2==0:
                        current_audio = last_chunk + chunk_total
                        # 只保留当前块的最后16个字节
                        last_chunk = current_audio[-overlap:]  # 这里可以根据实际音频样本长度调整
                        queue.put({
                            "data": current_audio,
                            "end": False
                        })
                        chunk_total = b''
                if len(chunk_total) > 0:
                    current_audio = last_chunk + chunk_total
                    queue.put({
                        "data": current_audio,
                        "end": False
                    })

            else:
                print('请求失败:', response.status_code, response.text)
        queue.put({
            "data": None,
            "end": True
        })

    async def text_to_speak(self, text, output_file):
        raise "不支持"


class DoubaoTTS(TTS):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.appid = config.get("appid")
        self.access_token = config.get("access_token")
        self.cluster = config.get("cluster")
        self.voice = config.get("voice")

        self.host = "openspeech.bytedance.com"
        self.api_url = f"https://{self.host}/api/v1/tts"
        self.header = {"Authorization": f"Bearer;{self.access_token}"}

    def generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    async def text_to_speak(self, text, output_file):
        request_json = {
            "app": {
                "appid": self.appid,
                "token": "access_token",
                "cluster": self.cluster
            },
            "user": {
                "uid": "1"
            },
            "audio": {
                "voice_type": self.voice,
                "encoding": "wav",
                "speed_ratio": 1.0,
                "volume_ratio": 1.0,
                "pitch_ratio": 1.0,
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "text_type": "plain",
                "operation": "query",
                "with_frontend": 1,
                "frontend_type": "unitTson"
            }
        }

        resp = requests.post(self.api_url, json.dumps(request_json), headers=self.header)
        if "data" in resp.json():
            data = resp.json()["data"]
            file_to_save = open(output_file, "wb")
            file_to_save.write(base64.b64decode(data))


def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls_map = {
        "DoubaoTTS": DoubaoTTS,
        "EdgeTTS": EdgeTTS,
        "GPT_SoVits": GPT_SoVits_TTS,
        "CosyVoiceTTS": CosyVoice_TTS,
        "FishSpeechTTS": FishSpeech_TTS
        # 可扩展其他TTS实现
    }

    if cls := cls_map.get(class_name):
        return cls(*args, **kwargs)
    raise ValueError(f"不支持的TTS类型: {class_name}")


if __name__ == "__main__":
    executor = ThreadPoolExecutor(max_workers=10)
    config = read_config(get_project_dir() + "config.yaml")
    tts = create_instance(
        config["selected_module"]["TTS"],
        config["TTS"][config["selected_module"]["TTS"]],
        config["delete_audio"]
    )


    def save_audio_to_file(audio_data, filename):
        with wave.open(filename, 'wb') as wf:
            # 假设音频数据是 PCM 格式，设置音频文件的参数
            wf.setnchannels(1)  # 单声道
            wf.setsampwidth(2)  # 16位音频
            wf.setframerate(44100)  # 采样率16kHz
            wf.writeframes(audio_data)


    def speak_and_play_queue(text, tts_queque):
        if text is None or len(text) <= 0:
            print(f"无需tts转换，query为空，{text}")
            return None
        tts.to_tts_stream_queue(text, tts_queque)
        if tts_queque is None:
            print(f"tts转换失败，{text}")


    tts_queque = queue.Queue()
    future = executor.submit(speak_and_play_queue,
                             "你好呀！我是野原新之助，小新！我今年5岁，是双叶幼稚园的小朋友，喜欢调皮捣蛋和恶作剧哦！你有什么想问我的呢？",
                             tts_queque)
    # tts_queque, tts_text = future.result()
    audio_data = b''
    start_time = time.time()
    while True:
        # 尝试获取数据，如果没有数据，则等待一小段时间再试
        audio_data_chunke = tts_queque.get()  # 设置超时为1秒
        if not audio_data_chunke:
            # 如果没有数据，继续等待
            if time.time() - start_time > 5:
                print("超过5秒没有数据，退出。")
                break
            continue

        audio_data_chunke_data = audio_data_chunke.get('data')

        # 检查是否超过 5 秒没有数据
        # if time.time() - start_time > 5:
        #     print("超过5秒没有数据，退出。")
        #     break

        if audio_data_chunke.get("end", True):
            break

        if audio_data_chunke_data:
            audio_data += audio_data_chunke_data
            opus_datas, duration = tts.wav_to_opus_data_audio(audio_data_chunke_data, type_format="wav")
            print(f"已获取音频数据，长度为 {len(audio_data_chunke_data)}，总长度为 {len(audio_data)}")
            start_time = time.time()  # 更新获取数据的时间
    future.result()
    # 保存音频数据到文件
    tts_speech = torch.from_numpy(np.array(np.frombuffer(audio_data, dtype=np.int16))).unsqueeze(dim=0)
    torchaudio.save("output.wav", tts_speech, 44100)
    print("音频文件已保存为 output.wav")
