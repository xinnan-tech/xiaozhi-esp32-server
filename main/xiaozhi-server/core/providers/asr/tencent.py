import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
import os
import uuid
from typing import Optional, Tuple, List
import wave
import opuslib_next

import requests
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

class ASRProvider(ASRProviderBase):
    API_URL = "https://asr.tencentcloudapi.com"
    API_VERSION = "2019-06-14"
    FORMAT = "pcm"  # 支持的音频格式：pcm, wav, mp3

    def __init__(self, config: dict, delete_audio_file: bool = True):
        self.secret_id = config.get("secret_id")
        self.secret_key = config.get("secret_key")
        self.output_dir = config.get("output_dir")
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def save_audio_to_file(self, opus_data: List[bytes], session_id: str) -> str:
        """将Opus音频数据解码并保存为WAV文件"""

        file_name = f"tencent_asr_{session_id}_{uuid.uuid4()}.wav"
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
    def decode_opus(opus_data: List[bytes]) -> bytes:
        """将Opus音频数据解码为PCM数据"""
        import opuslib_next
        
        decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
        pcm_data = []
        
        for opus_packet in opus_data:
            try:
                pcm_frame = decoder.decode(opus_packet, 960)  # 960 samples = 60ms
                pcm_data.append(pcm_frame)
            except opuslib_next.OpusError as e:
                logger.bind(tag=TAG).error(f"Opus解码错误: {e}", exc_info=True)
        
        return b"".join(pcm_data)

    async def speech_to_text(self, opus_data: List[bytes], session_id: str) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""
        if not opus_data:
            logger.bind(tag=TAG).warn("音频数据为空！")
            return None, None

        try:
            # 检查配置是否已设置
            if not self.secret_id or not self.secret_key:
                logger.bind(tag=TAG).error("腾讯云语音识别配置未设置，无法进行识别")
                return None, None

            # 将Opus音频数据解码为PCM
            pcm_data = self.decode_opus(opus_data)
            
            # 将音频数据转换为Base64编码
            base64_audio = base64.b64encode(pcm_data).decode('utf-8')

            # 构建请求体
            request_body = self._build_request_body(base64_audio)

            # 获取认证头
            timestamp, authorization = self._get_auth_headers(request_body)

            # 发送请求
            start_time = time.time()
            result = self._send_request(request_body, timestamp, authorization)
            
            if result:
                logger.bind(tag=TAG).debug(f"腾讯云语音识别耗时: {time.time() - start_time:.3f}s | 结果: {result}")
            
            return result, None

        except Exception as e:
            logger.bind(tag=TAG).error(f"处理音频时发生错误！{e}", exc_info=True)
            return None, None

    def _build_request_body(self, base64_audio: str) -> str:
        """构建请求体"""
        request_map = {
            "ProjectId": 0,
            "SubServiceType": 2,  # 一句话识别
            "EngSerViceType": "16k_zh",  # 中文普通话通用
            "SourceType": 1,  # 音频数据来源为语音文件
            "VoiceFormat": self.FORMAT,  # 音频格式
            "Data": base64_audio,  # Base64编码的音频数据
            "DataLen": len(base64_audio)  # 数据长度
        }
        return json.dumps(request_map)

    def _get_auth_headers(self, request_body: str) -> Tuple[str, str]:
        """获取认证头"""
        try:
            # 获取当前UTC时间戳
            now = datetime.now(timezone.utc)
            timestamp = str(int(now.timestamp()))
            date = now.strftime("%Y-%m-%d")

            # 服务名称必须是 "asr"
            service = "asr"

            # 拼接凭证范围
            credential_scope = f"{date}/{service}/tc3_request"

            # 使用TC3-HMAC-SHA256签名方法
            algorithm = "TC3-HMAC-SHA256"

            # 构建规范请求字符串
            http_request_method = "POST"
            canonical_uri = "/"
            canonical_query_string = ""

            # 注意：头部信息需要按照ASCII升序排列，且key和value都转为小写
            # 必须包含content-type和host头部
            content_type = "application/json; charset=utf-8"
            host = "asr.tencentcloudapi.com"
            action = "SentenceRecognition"  # 接口名称

            # 构建规范头部信息，注意顺序和格式
            canonical_headers = f"content-type:{content_type.lower()}\n" + \
                               f"host:{host.lower()}\n" + \
                               f"x-tc-action:{action.lower()}\n"

            signed_headers = "content-type;host;x-tc-action"

            # 请求体哈希值
            payload_hash = self._sha256_hex(request_body)

            # 构建规范请求字符串
            canonical_request = f"{http_request_method}\n" + \
                               f"{canonical_uri}\n" + \
                               f"{canonical_query_string}\n" + \
                               f"{canonical_headers}\n" + \
                               f"{signed_headers}\n" + \
                               f"{payload_hash}"

            # 计算规范请求的哈希值
            hashed_canonical_request = self._sha256_hex(canonical_request)

            # 构建待签名字符串
            string_to_sign = f"{algorithm}\n" + \
                            f"{timestamp}\n" + \
                            f"{credential_scope}\n" + \
                            f"{hashed_canonical_request}"

            # 计算签名密钥
            secret_date = self._hmac_sha256(f"TC3{self.secret_key}", date)
            secret_service = self._hmac_sha256(secret_date, service)
            secret_signing = self._hmac_sha256(secret_service, "tc3_request")

            # 计算签名
            signature = self._bytes_to_hex(self._hmac_sha256(secret_signing, string_to_sign))

            # 构建授权头
            authorization = f"{algorithm} " + \
                           f"Credential={self.secret_id}/{credential_scope}, " + \
                           f"SignedHeaders={signed_headers}, " + \
                           f"Signature={signature}"

            return timestamp, authorization

        except Exception as e:
            logger.bind(tag=TAG).error(f"生成认证头失败: {e}", exc_info=True)
            raise RuntimeError(f"生成认证头失败: {e}")

    def _send_request(self, request_body: str, timestamp: str, authorization: str) -> Optional[str]:
        """发送请求到腾讯云API"""
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Host": "asr.tencentcloudapi.com",
            "Authorization": authorization,
            "X-TC-Action": "SentenceRecognition",
            "X-TC-Version": self.API_VERSION,
            "X-TC-Timestamp": timestamp,
            "X-TC-Region": "ap-shanghai"
        }

        try:
            response = requests.post(self.API_URL, headers=headers, data=request_body)
            
            if not response.ok:
                raise IOError(f"请求失败: {response.status_code} {response.reason}")
            
            response_json = response.json()
            
            # 检查是否有错误
            if "Response" in response_json and "Error" in response_json["Response"]:
                error = response_json["Response"]["Error"]
                error_code = error["Code"]
                error_message = error["Message"]
                raise IOError(f"API返回错误: {error_code}: {error_message}")
            
            # 提取识别结果
            if "Response" in response_json and "Result" in response_json["Response"]:
                return response_json["Response"]["Result"]
            else:
                logger.bind(tag=TAG).warn(f"响应中没有识别结果: {response_json}")
                return ""
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"发送请求失败: {e}", exc_info=True)
            return None

    def _sha256_hex(self, data: str) -> str:
        """计算字符串的SHA256哈希值"""
        digest = hashlib.sha256(data.encode('utf-8')).digest()
        return self._bytes_to_hex(digest)

    def _hmac_sha256(self, key, data: str) -> bytes:
        """计算HMAC-SHA256"""
        if isinstance(key, str):
            key = key.encode('utf-8')
        
        return hmac.new(key, data.encode('utf-8'), hashlib.sha256).digest()

    def _bytes_to_hex(self, bytes_data: bytes) -> str:
        """字节数组转十六进制字符串"""
        return ''.join(f"{b:02x}" for b in bytes_data)