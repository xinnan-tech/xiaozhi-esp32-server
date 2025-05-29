import http.client
import json
import asyncio
from typing import Optional, Tuple, List
import opuslib_next
import wave
import io
import os
import uuid
import hmac
import hashlib
import base64
import requests
from urllib import parse
import time
from datetime import datetime
from config.logger import setup_logging
from core.providers.asr.base import ASRProviderBase

TAG = __name__
logger = setup_logging()


class AccessToken:
    @staticmethod
    def _encode_text(text):
        encoded_text = parse.quote_plus(text)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def _encode_dict(dic):
        keys = dic.keys()
        dic_sorted = [(key, dic[key]) for key in sorted(keys)]
        encoded_text = parse.urlencode(dic_sorted)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def create_token(access_key_id, access_key_secret):
        parameters = {
            "AccessKeyId": access_key_id,
            "Action": "CreateToken",
            "Format": "JSON",
            "RegionId": "cn-shanghai",
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid1()),
            "SignatureVersion": "1.0",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "Version": "2019-02-28",
        }
        # 构造规范化的请求字符串
        query_string = AccessToken._encode_dict(parameters)
        # print('规范化的请求字符串: %s' % query_string)
        # 构造待签名字符串
        string_to_sign = (
            "GET"
            + "&"
            + AccessToken._encode_text("/")
            + "&"
            + AccessToken._encode_text(query_string)
        )
        # print('待签名的字符串: %s' % string_to_sign)
        # 计算签名
        secreted_string = hmac.new(
            bytes(access_key_secret + "&", encoding="utf-8"),
            bytes(string_to_sign, encoding="utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(secreted_string)
        # print('签名: %s' % signature)
        # 进行URL编码
        signature = AccessToken._encode_text(signature)
        # print('URL编码后的签名: %s' % signature)
        # 调用服务
        full_url = "http://nls-meta.cn-shanghai.aliyuncs.com/?Signature=%s&%s" % (
            signature,
            query_string,
        )
        # print('url: %s' % full_url)
        # 提交HTTP GET请求
        response = requests.get(full_url)
        if response.ok:
            root_obj = response.json()
            key = "Token"
            if key in root_obj:
                token = root_obj[key]["Id"]
                expire_time = root_obj[key]["ExpireTime"]
                return token, expire_time
        # print(response.text)
        return None, None


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        """阿里云ASR初始化"""
        # 新增空值判断逻辑
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")

        self.app_key = config.get("appkey")
        self.host = "nls-gateway-cn-shanghai.aliyuncs.com"
        self.base_url = f"https://{self.host}/stream/v1/asr"
        self.sample_rate = 16000
        self.format = "wav"
        self.output_dir = config.get("output_dir", "./audio_output")
        self.delete_audio_file = delete_audio_file

        if self.access_key_id and self.access_key_secret:
            # 使用密钥对生成临时token
            self._refresh_token()
        else:
            # 直接使用预生成的长期token
            self.token = config.get("token")
            self.expire_time = None

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def _refresh_token(self):
        """刷新Token并记录过期时间"""
        if self.access_key_id and self.access_key_secret:
            self.token, expire_time_str = AccessToken.create_token(
                self.access_key_id, self.access_key_secret
            )
            if not expire_time_str:
                raise ValueError("无法获取有效的Token过期时间")

            try:
                # 统一转换为字符串处理
                expire_str = str(expire_time_str).strip()

                if expire_str.isdigit():
                    expire_time = datetime.fromtimestamp(int(expire_str))
                else:
                    expire_time = datetime.strptime(expire_str, "%Y-%m-%dT%H:%M:%SZ")
                self.expire_time = expire_time.timestamp() - 60
            except Exception as e:
                raise ValueError(f"无效的过期时间格式: {expire_str}") from e

        else:
            self.expire_time = None

        if not self.token:
            raise ValueError("无法获取有效的访问Token")

    def _is_token_expired(self):
        """检查Token是否过期"""
        if not self.expire_time:
            return False  # 长期Token不过期
        # 新增调试日志
        # current_time = time.time()
        # remaining = self.expire_time - current_time
        # print(f"Token过期检查: 当前时间 {datetime.fromtimestamp(current_time)} | "
        #              f"过期时间 {datetime.fromtimestamp(self.expire_time)} | "
        #              f"剩余 {remaining:.2f}秒")
        return time.time() > self.expire_time

    def _construct_request_url(self) -> str:
        """构造请求URL，包含参数"""
        request = f"{self.base_url}?appkey={self.app_key}"
        request += f"&format={self.format}"
        request += f"&sample_rate={self.sample_rate}"
        request += "&enable_punctuation_prediction=true"
        request += "&enable_inverse_text_normalization=true"
        request += "&enable_voice_detection=false"
        return request

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """PCM数据保存为WAV文件"""
        module_name = __name__.split(".")[-1]
        file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)  # 单声道
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(b"".join(pcm_data))

        logger.bind(tag=TAG).debug(f"音频文件已保存至: {file_path}")
        return file_path

    async def _send_request(self, pcm_data: bytes) -> Optional[str]:
        """发送请求到阿里云ASR服务"""
        try:
            # 设置HTTP头
            headers = {
                "X-NLS-Token": self.token,
                "Content-type": "application/octet-stream",
                "Content-Length": str(len(pcm_data)),
            }

            # 创建连接并发送请求
            conn = http.client.HTTPSConnection(self.host)
            request_url = self._construct_request_url()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: conn.request(
                    method="POST", url=request_url, body=pcm_data, headers=headers
                ),
            )

            # 获取响应
            response = await loop.run_in_executor(None, conn.getresponse)
            body = await loop.run_in_executor(None, response.read)
            conn.close()

            # 解析响应
            try:
                body_json = json.loads(body)
                status = body_json.get("status")

                if status == 20000000:
                    result = body_json.get("result", "")
                    logger.bind(tag=TAG).debug(f"ASR结果: {result}")
                    return result
                else:
                    logger.bind(tag=TAG).error(f"ASR失败，状态码: {status}")
                    return None

            except ValueError:
                logger.bind(tag=TAG).error("响应不是JSON格式")
                return None

        except Exception as e:
            logger.bind(tag=TAG).error(f"ASR请求失败: {e}", exc_info=True)
            return None

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """将语音数据转换为文本"""
        if self._is_token_expired():
            logger.warning("Token已过期，正在自动刷新...")
            self._refresh_token()

        file_path = None
        try:
            # 解码Opus为PCM
            if self.audio_format == "pcm":
                pcm_data = opus_data
            else:
                pcm_data = self.decode_opus(opus_data)
            combined_pcm_data = b"".join(pcm_data)

            # 判断是否保存为WAV文件
            if self.delete_audio_file:
                pass
            else:
                file_path = self.save_audio_to_file(pcm_data, session_id)

            # 发送请求并获取文本
            text = await self._send_request(combined_pcm_data)

            if text:
                return text, file_path

            return "", file_path

        except Exception as e:
            logger.bind(tag=TAG).error(f"语音识别失败: {e}", exc_info=True)
            return "", file_path
