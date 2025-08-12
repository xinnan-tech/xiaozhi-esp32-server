import asyncio
import json
import base64
import aiohttp
import numpy as np
import io
import wave
import websockets
from core.providers.tts.base import TTSProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get("url", "ws://192.168.1.10:8092/paddlespeech/tts/streaming")
        self.protocol = config.get("protocol", "websocket")
        self.spk_id = config.get("spk_id", 0)
        self.sample_rate = config.get("sample_rate", 24000)
        self.speed = config.get("speed", 1.0)
        self.volume = config.get("volume", 1.0)
        self.save_path = config.get("save_path", "./streaming_tts.wav")

    async def pcm_to_wav(self, pcm_data: bytes, sample_rate: int = 24000, num_channels: int = 1,
                         bits_per_sample: int = 16) -> bytes:
        """
        将 PCM 数据转换为 WAV 文件并返回字节数据
        :param pcm_data: PCM 数据（原始字节流）
        :param sample_rate: 音频采样率，默认为24000
        :param num_channels: 声道数，默认为单声道
        :param bits_per_sample: 每个样本的位数，默认为16
        :return: WAV 格式的字节数据
        """
        byte_data = np.frombuffer(pcm_data, dtype=np.int16)  # 16位PCM
        wav_io = io.BytesIO()

        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(bits_per_sample // 8)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(byte_data.tobytes())

        return wav_io.getvalue()

    async def text_to_speak(self, text, output_file):
        if self.protocol == "websocket":
            return await self.text_streaming(text, output_file)
        elif self.protocol == "http":
            return await self.text(text, output_file)
        else:
            raise ValueError("Unsupported protocol. Please use 'websocket' or 'http'.")

    async def text(self, text, output_file):
        request_json = {
            "text": text,
            "spk_id": self.spk_id,
            "speed": self.speed,
            "volume": self.volume,
            "sample_rate": self.sample_rate,
            "save_path": self.save_path
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.url, json=request_json) as resp:
                    if resp.status == 200:
                        resp_json = await resp.json()
                        if resp_json.get("success"):
                            data = resp_json["result"]
                            audio_bytes = base64.b64decode(data["audio"])
                            if output_file:
                                with open(output_file, "wb") as file_to_save:
                                    file_to_save.write(audio_bytes)
                            else:
                                return audio_bytes
                        else:
                            raise Exception(
                                f"Error: {resp_json.get('message', 'Unknown error')} while processing text: {text}")
                    else:
                        raise Exception(
                            f"HTTP Error: {resp.status} - {await resp.text()} while processing text: {text}")
        except Exception as e:
            raise Exception(f"Error during TTS HTTP request: {e} while processing text: {text}")

    async def text_streaming(self, text, output_file):
        try:
            # 使用 websockets 异步连接到 WebSocket 服务器
            async with websockets.connect(self.url) as ws:
                # 发送开始请求
                start_request = {
                    "task": "tts",
                    "signal": "start"
                }
                await ws.send(json.dumps(start_request))

                # 接收开始响应并提取 session_id
                start_response = await ws.recv()
                start_response = json.loads(start_response)  # 解析 JSON 响应
                if start_response.get("status") != 0:
                    raise Exception(f"连接失败: {start_response.get('signal')}")

                session_id = start_response.get("session")

                # 发送待合成的文本数据
                data_request = {
                    "text": text,
                    "spk_id": self.spk_id,
                }
                await ws.send(json.dumps(data_request))

                audio_chunks = b""
                timeout_seconds = 60  # 设置超时
                try:
                    while True:
                        response = await asyncio.wait_for(ws.recv(), timeout=timeout_seconds)
                        response = json.loads(response)  # 解析 JSON 响应
                        status = response.get("status")

                        if status == 2:  # 最后一个数据包
                            break
                        else:
                            # 拼接音频数据（base64 编码的 PCM 数据）
                            audio_chunks += base64.b64decode(response.get("audio"))
                except asyncio.TimeoutError:
                    raise Exception(f"WebSocket 超时：等待音频数据超过 {timeout_seconds} 秒")

                # 将拼接后的 PCM 数据转换为 WAV 格式
                wav_data = await self.pcm_to_wav(audio_chunks)

                # 结束请求
                end_request = {
                    "task": "tts",
                    "signal": "end",
                    "session": session_id  # 会话 ID 必须与开始请求中的一致
                }
                await ws.send(json.dumps(end_request))

                # 接收结束响应避免服务抛出异常
                await ws.recv()

                # 返回或保存音频数据
                if output_file:
                    with open(output_file, "wb") as file_to_save:
                        file_to_save.write(wav_data)
                else:
                    return wav_data

        except Exception as e:
            raise Exception(f"Error during TTS WebSocket request: {e} while processing text: {text}")