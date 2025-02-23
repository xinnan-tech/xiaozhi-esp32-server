import time
import io
import wave
import os
from typing import Optional, Tuple, List
import uuid
import websockets
import json
import gzip

import opuslib_next
from core.providers.asr.base import ASRProviderBase

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

CLIENT_FULL_REQUEST = 0b0001
CLIENT_AUDIO_ONLY_REQUEST = 0b0010

NO_SEQUENCE = 0b0000
NEG_SEQUENCE = 0b0010

SERVER_FULL_RESPONSE = 0b1001
SERVER_ACK = 0b1011
SERVER_ERROR_RESPONSE = 0b1111

NO_SERIALIZATION = 0b0000
JSON = 0b0001
THRIFT = 0b0011
CUSTOM_TYPE = 0b1111
NO_COMPRESSION = 0b0000
GZIP = 0b0001
CUSTOM_COMPRESSION = 0b1111


def parse_response(res):
    """
    protocol_version(4 bits), header_size(4 bits),
    message_type(4 bits), message_type_specific_flags(4 bits)
    serialization_method(4 bits) message_compression(4 bits)
    reserved （8bits) 保留字段
    header_extensions 扩展头(大小等于 8 * 4 * (header_size - 1) )
    payload 类似与http 请求体
    """
    protocol_version = res[0] >> 4
    header_size = res[0] & 0x0f
    message_type = res[1] >> 4
    message_type_specific_flags = res[1] & 0x0f
    serialization_method = res[2] >> 4
    message_compression = res[2] & 0x0f
    reserved = res[3]
    header_extensions = res[4:header_size * 4]
    payload = res[header_size * 4:]
    result = {}
    payload_msg = None
    payload_size = 0
    if message_type == SERVER_FULL_RESPONSE:
        payload_size = int.from_bytes(payload[:4], "big", signed=True)
        payload_msg = payload[4:]
    elif message_type == SERVER_ACK:
        seq = int.from_bytes(payload[:4], "big", signed=True)
        result['seq'] = seq
        if len(payload) >= 8:
            payload_size = int.from_bytes(payload[4:8], "big", signed=False)
            payload_msg = payload[8:]
    elif message_type == SERVER_ERROR_RESPONSE:
        code = int.from_bytes(payload[:4], "big", signed=False)
        result['code'] = code
        payload_size = int.from_bytes(payload[4:8], "big", signed=False)
        payload_msg = payload[8:]
    if payload_msg is None:
        return result
    if message_compression == GZIP:
        payload_msg = gzip.decompress(payload_msg)
    if serialization_method == JSON:
        payload_msg = json.loads(str(payload_msg, "utf-8"))
    elif serialization_method != NO_SERIALIZATION:
        payload_msg = str(payload_msg, "utf-8")
    result['payload_msg'] = payload_msg
    result['payload_size'] = payload_size
    return result


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        self.appid = config.get("appid")
        self.cluster = config.get("cluster")
        self.access_token = config.get("access_token")
        self.output_dir = config.get("output_dir")

        self.host = "openspeech.bytedance.com"
        self.ws_url = f"wss://{self.host}/api/v2/asr"
        self.success_code = 1000
        self.seg_duration = 15000

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def save_audio_to_file(self, opus_data: List[bytes], session_id: str) -> str:
        """将Opus音频数据解码并保存为WAV文件"""
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

    @staticmethod
    def _generate_header(message_type=CLIENT_FULL_REQUEST, message_type_specific_flags=NO_SEQUENCE) -> bytearray:
        """Generate protocol header."""
        header = bytearray()
        header_size = 1
        header.append((0b0001 << 4) | header_size)  # Protocol version
        header.append((message_type << 4) | message_type_specific_flags)
        header.append((0b0001 << 4) | 0b0001)  # JSON serialization & GZIP compression
        header.append(0x00)  # reserved
        return header

    def _construct_request(self, reqid) -> dict:
        """Construct the request payload."""
        return {
            "app": {
                "appid": f"{self.appid}",
                "cluster": self.cluster,
                "token": self.access_token,
            },
            "user": {
                "uid": str(uuid.uuid4()),
            },
            "request": {
                "reqid": reqid,
                "show_utterances": False,
                "sequence": 1
            },
            "audio": {
                "format": "wav",
                "rate": 16000,
                "language": "zh-CN",
                "bits": 16,
                "channel": 1,
                "codec": "raw",
            },
        }

    async def _send_request(self, audio_data: List[bytes], segment_size: int) -> Optional[str]:
        """Send request to Volcano ASR service."""
        try:
            auth_header = {'Authorization': 'Bearer; {}'.format(self.access_token)}
            async with websockets.connect(self.ws_url, additional_headers=auth_header) as websocket:
                # Prepare request data
                request_params = self._construct_request(str(uuid.uuid4()))
                print(request_params)
                payload_bytes = str.encode(json.dumps(request_params))
                payload_bytes = gzip.compress(payload_bytes)
                full_client_request = self._generate_header()
                full_client_request.extend((len(payload_bytes)).to_bytes(4, 'big'))  # payload size(4 bytes)
                full_client_request.extend(payload_bytes)  # payload

                # Send header and metadata
                # full_client_request
                await websocket.send(full_client_request)
                res = await websocket.recv()
                result = parse_response(res)
                if 'payload_msg' in result and result['payload_msg']['code'] != self.success_code:
                    logger.bind(tag=TAG).error(f"ASR error: {result}")
                    return None

                for seq, (chunk, last) in enumerate(self.slice_data(audio_data, segment_size), 1):
                    if last:
                        audio_only_request = self._generate_header(
                            message_type=CLIENT_AUDIO_ONLY_REQUEST,
                            message_type_specific_flags=NEG_SEQUENCE
                        )
                    else:
                        audio_only_request = self._generate_header(
                            message_type=CLIENT_AUDIO_ONLY_REQUEST
                        )
                    payload_bytes = gzip.compress(chunk)
                    audio_only_request.extend((len(payload_bytes)).to_bytes(4, 'big'))  # payload size(4 bytes)
                    audio_only_request.extend(payload_bytes)  # payload
                    # Send audio data
                    await websocket.send(audio_only_request)

                # Receive response
                response = await websocket.recv()
                result = parse_response(response)

                if 'payload_msg' in result and result['payload_msg']['code'] == self.success_code:
                    if len(result['payload_msg']['result']) > 0:
                        return result['payload_msg']['result'][0]["text"]
                    return None
                else:
                    logger.bind(tag=TAG).error(f"ASR error: {result}")
                    return None

        except Exception as e:
            logger.bind(tag=TAG).error(f"ASR request failed: {e}", exc_info=True)
            return None

    @staticmethod
    def decode_opus(opus_data: List[bytes], session_id: str) -> List[bytes]:

        decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
        pcm_data = []

        for opus_packet in opus_data:
            try:
                pcm_frame = decoder.decode(opus_packet, 960)  # 960 samples = 60ms
                pcm_data.append(pcm_frame)
            except opuslib_next.OpusError as e:
                logger.bind(tag=TAG).error(f"Opus解码错误: {e}", exc_info=True)

        return pcm_data

    @staticmethod
    def read_wav_info(data: io.BytesIO = None) -> (int, int, int, int, int):
        with io.BytesIO(data) as _f:
            wave_fp = wave.open(_f, 'rb')
            nchannels, sampwidth, framerate, nframes = wave_fp.getparams()[:4]
            wave_bytes = wave_fp.readframes(nframes)
        return nchannels, sampwidth, framerate, nframes, len(wave_bytes)

    @staticmethod
    def slice_data(data: bytes, chunk_size: int) -> (list, bool):
        """
        slice data
        :param data: wav data
        :param chunk_size: the segment size in one request
        :return: segment data, last flag
        """
        data_len = len(data)
        offset = 0
        while offset + chunk_size < data_len:
            yield data[offset: offset + chunk_size], False
            offset += chunk_size
        else:
            yield data[offset: data_len], True

    async def speech_to_text(self, opus_data: List[bytes], session_id: str) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""
        try:
            # 合并所有opus数据包
            pcm_data = self.decode_opus(opus_data, session_id)
            combined_pcm_data = b''.join(pcm_data)

            wav_buffer = io.BytesIO()

            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)  # 设置声道数
                wav_file.setsampwidth(2)  # 设置采样宽度
                wav_file.setframerate(16000)  # 设置采样率
                wav_file.writeframes(combined_pcm_data)  # 写入 PCM 数据

            # 获取封装后的 WAV 数据
            wav_data = wav_buffer.getvalue()
            nchannels, sampwidth, framerate, nframes, wav_len = self.read_wav_info(wav_data)
            size_per_sec = nchannels * sampwidth * framerate
            segment_size = int(size_per_sec * self.seg_duration / 1000)

            # 语音识别
            start_time = time.time()
            text = await self._send_request(wav_data, segment_size)
            if text:
                logger.bind(tag=TAG).debug(f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {text}")
                return text, None
            return "", None

        except Exception as e:
            logger.bind(tag=TAG).error(f"语音识别失败: {e}", exc_info=True)
            return "", None
