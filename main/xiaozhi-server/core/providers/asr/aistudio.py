import os
import time
import uuid
import wave
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging
import opuslib_next
import requests

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        self.scope = config.get("scope")
        self.dev_pid = config.get("dev_pid")
        self.output_dir = config.get("output_dir")

        self.asr_url = "http://vop.baidu.com/server_api"
        self.token = self.fetch_token(config.get("api_key"), config.get("secret_key"))

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def save_audio_to_file(self, opus_data: list[bytes], session_id: str) -> str:
        """解码Opus数据并保存为WAV文件"""
        file_name = f"asr_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
        pcm_data = []

        for opus_packet in opus_data:
            try:
                pcm_frame = decoder.decode(opus_packet, 960)  # 960 samples = 60ms
                pcm_data.append(pcm_frame)
            except opuslib_next.OpusError as e:
                logger.bind(tag=TAG).error(f"Opus解码错误: {e}", exc_info=True)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    def fetch_token(self, api_key: str, secret_key: str) -> str:
        """Fetch access token from Baidu API using requests."""
        params = {"grant_type": "client_credentials", "client_id": api_key, "client_secret": secret_key}

        try:
            response = requests.get("https://openapi.baidu.com/oauth/2.0/token", params=params)
            response.raise_for_status()  # 抛出HTTP错误
            result = response.json()

            access_token = result.get("access_token")
            scope = result.get("scope")

            if not access_token or self.scope not in (scope or ""):
                raise RuntimeError("Failed to fetch token or scope is incorrect.")

            return access_token

        except requests.RequestException as e:
            raise RuntimeError(f"Token request failed: {e}") from e


    @staticmethod
    def decode_opus(opus_data: list[bytes]) -> bytes:
        """将Opus音频数据解码为PCM数据"""
        decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
        pcm_data = []

        for opus_packet in opus_data:
            try:
                pcm_frame = decoder.decode(opus_packet, 960)  # 960 samples = 60ms
                pcm_data.append(pcm_frame)
            except opuslib_next.OpusError as e:
                logger.bind(tag=TAG).error(f"Opus解码错误: {e}", exc_info=True)

        return b"".join(pcm_data)

    def _build_request_body(self, file_format: str = "wav") -> tuple[dict, dict]:
        params = {
            'cuid': self.cuid,
            'token': self.token,
            'dev_pid': self.dev_pid,
        }

        headers = {
            'Content-Type': f'audio/{file_format}; rate={self.rate}'
        }
        return params, headers

    def _send_request(self, pcm_data: bytes, params: dict, headers: dict) -> dict:
        response = requests.post(
            self.asr_url,
            params=params,
            data=pcm_data,
            headers=headers,
            timeout=10  # 设置超时时间
        )
        response.raise_for_status()  # 检查HTTP错误
        return response.json()

    async def speech_to_text(self, opus_data: list[bytes], session_id: str) -> list[str | None, str | None]:
        """将语音数据转换为文本"""
        if not opus_data:
            logger.bind(tag=TAG).warn("音频数据为空！")
            return None, None

        try:
            # 将Opus音频数据解码为PCM
            pcm_data = self.decode_opus(opus_data)
            params, headers = self._build_request_body()

            # 发送请求
            start_time = time.time()
            result = self._send_request(pcm_data, params, headers)

            if result:
                logger.bind(tag=TAG).debug(f"aistudio 语音识别耗时: {time.time() - start_time:.3f}s | 结果: {result}")

            # TODO: 可能需要处理异常结果
            return result, None

        except Exception as e:
            logger.bind(tag=TAG).error(f"处理音频时发生错误！{e}", exc_info=True)
            return None, None
