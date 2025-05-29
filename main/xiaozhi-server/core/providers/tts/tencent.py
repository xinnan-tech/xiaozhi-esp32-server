import hashlib
import hmac
import time
import uuid
import json
import base64
import requests
from datetime import datetime, timezone
from core.providers.tts.base import TTSProviderBase


class TTSProvider(TTSProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.appid = config.get("appid")
        self.secret_id = config.get("secret_id")
        self.secret_key = config.get("secret_key")
        if config.get("private_voice"):
            self.voice = config.get("private_voice")
        else:
            self.voice = int(config.get("voice"))
        self.api_url = "https://tts.tencentcloudapi.com"  # 正确的API端点
        self.region = config.get("region")
        self.output_file = config.get("output_dir")

    def _get_auth_headers(self, request_body):
        """生成鉴权请求头"""
        # 获取当前UTC时间戳
        timestamp = int(time.time())

        # 使用UTC时间计算日期
        utc_date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(
            "%Y-%m-%d"
        )

        # 服务名称必须是 "tts"
        service = "tts"

        # 拼接凭证范围
        credential_scope = f"{utc_date}/{service}/tc3_request"

        # 使用TC3-HMAC-SHA256签名方法
        algorithm = "TC3-HMAC-SHA256"

        # 构建规范请求字符串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""

        # 请求头必须包含host和content-type，且按字典序排列
        canonical_headers = (
            f"content-type:application/json\n" f"host:tts.tencentcloudapi.com\n"
        )
        signed_headers = "content-type;host"

        # 请求体哈希值
        payload = json.dumps(request_body)
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        # 构建规范请求字符串
        canonical_request = (
            f"{http_request_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        # 计算规范请求的哈希值
        hashed_canonical_request = hashlib.sha256(
            canonical_request.encode("utf-8")
        ).hexdigest()

        # 构建待签名字符串
        string_to_sign = (
            f"{algorithm}\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{hashed_canonical_request}"
        )

        # 计算签名密钥
        secret_date = self._hmac_sha256(
            f"TC3{self.secret_key}".encode("utf-8"), utc_date
        )
        secret_service = self._hmac_sha256(secret_date, service)
        secret_signing = self._hmac_sha256(secret_service, "tc3_request")

        # 计算签名
        signature = hmac.new(
            secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # 构建授权头
        authorization = (
            f"{algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Host": "tts.tencentcloudapi.com",
            "Authorization": authorization,
            "X-TC-Action": "TextToVoice",
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": "2019-08-23",
            "X-TC-Region": self.region,
            "X-TC-Language": "zh-CN",
        }

        return headers

    def _hmac_sha256(self, key, msg):
        """HMAC-SHA256加密"""
        if isinstance(msg, str):
            msg = msg.encode("utf-8")
        return hmac.new(key, msg, hashlib.sha256).digest()

    async def text_to_speak(self, text, output_file):
        # 构建请求体
        request_json = {
            "Text": text,  # 合成语音的源文本
            "SessionId": str(uuid.uuid4()),  # 会话ID，随机生成
            "VoiceType": int(self.voice),  # 音色
        }

        try:
            # 获取请求头（每次请求都重新生成，以确保时间戳和签名是最新的）
            headers = self._get_auth_headers(request_json)

            # 发送请求
            resp = requests.post(
                self.api_url, json.dumps(request_json), headers=headers
            )

            # 检查响应
            if resp.status_code == 200:
                response_data = resp.json()

                # 检查是否成功
                if response_data.get("Response", {}).get("Error") is not None:
                    error_info = response_data["Response"]["Error"]
                    raise Exception(
                        f"API返回错误: {error_info['Code']}: {error_info['Message']}"
                    )

                # 提取音频数据
                audio_data = response_data["Response"].get("Audio")
                if audio_data:
                    # 解码Base64音频数据并保存
                    with open(output_file, "wb") as f:
                        f.write(base64.b64decode(audio_data))
                else:
                    raise Exception(f"{__name__}: 没有返回音频数据: {response_data}")
            else:
                raise Exception(
                    f"{__name__} status_code: {resp.status_code} response: {resp.content}"
                )
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")
