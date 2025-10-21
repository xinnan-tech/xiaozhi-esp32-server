import http.client
import json
import asyncio
from typing import Optional, Tuple, List
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
from core.providers.asr.dto.dto import InterfaceType

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
        # Construct a normalized request string
        query_string = AccessToken._encode_dict(parameters)
        # print('Normalized request string: %s' % query_string)
        # Construct a string to be signed
        string_to_sign = (
            "GET"
            + "&"
            + AccessToken._encode_text("/")
            + "&"
            + AccessToken._encode_text(query_string)
        )
        # print('String to be signed: %s' % string_to_sign)
        # Compute signature
        secreted_string = hmac.new(
            bytes(access_key_secret + "&", encoding="utf-8"),
            bytes(string_to_sign, encoding="utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(secreted_string)
        # print('sign: %s' % signature)
        # perform url encoding
        signature = AccessToken._encode_text(signature)
        # print('Url encoded signature: %s' % signature)
        # Call service
        full_url = "http://nls-meta.cn-shanghai.aliyuncs.com/?Signature=%s&%s" % (
            signature,
            query_string,
        )
        # print('url: %s' % full_url)
        # Submit HTTP GET request
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
        self.interface_type = InterfaceType.NON_STREAM
        """Alibaba Cloud asr initialization"""
        # Added null value judgment logic
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
            # Generate temporary token using key pair
            self._refresh_token()
        else:
            # Use pre-generated long-term tokens directly
            self.token = config.get("token")
            self.expire_time = None

        # Make sure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def _refresh_token(self):
        """Refresh the token and record the expiration time"""
        if self.access_key_id and self.access_key_secret:
            self.token, expire_time_str = AccessToken.create_token(
                self.access_key_id, self.access_key_secret
            )
            if not expire_time_str:
                raise ValueError("Unable to obtain valid token expiration time")

            try:
                # Unified conversion to string processingnversion to string processing
                expire_str = str(expire_time_str).strip()

                if expire_str.isdigit():
                    expire_time = datetime.fromtimestamp(int(expire_str))
                else:
                    expire_time = datetime.strptime(expire_str, "%Y-%m-%dT%H:%M:%SZ")
                self.expire_time = expire_time.timestamp() - 60
            except Exception as e:
                raise ValueError(f"Invalid expiration time format: {expire_str}") from e

        else:
            self.expire_time = None

        if not self.token:
            raise ValueError("Unable to obtain valid access token")

    def _is_token_expired(self):
        """Check if the token has expired"""
        if not self.expire_time:
            return False  # Long-term tokens do not expire
        # Add debug log
        # current_time = time.time()
        # remaining = self.expire_time - current_time
        # print(f"Token expiration check: current time {datetime.fromtimestamp(current_time)} | "
        #              f"Expiration time {datetime.fromtimestamp(self.expire_time)} | "
        #              f"Remaining {remaining:.2f}Second")
        return time.time() > self.expire_time

    def _construct_request_url(self) -> str:
        """Construct the request url, including parameters"""
        request = f"{self.base_url}?appkey={self.app_key}"
        request += f"&format={self.format}"
        request += f"&sample_rate={self.sample_rate}"
        request += "&enable_punctuation_prediction=true"
        request += "&enable_inverse_text_normalization=true"
        request += "&enable_voice_detection=false"
        return request

    async def _send_request(self, pcm_data: bytes) -> Optional[str]:
        """Send a request to Alibaba Cloud ASR service"""
        try:
            # Set http header
            headers = {
                "X-NLS-Token": self.token,
                "Content-type": "application/octet-stream",
                "Content-Length": str(len(pcm_data)),
            }

            # Create connection and send request
            conn = http.client.HTTPSConnection(self.host)
            request_url = self._construct_request_url()

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: conn.request(
                    method="POST", url=request_url, body=pcm_data, headers=headers
                ),
            )

            # Get response
            response = await loop.run_in_executor(None, conn.getresponse)
            body = await loop.run_in_executor(None, response.read)
            conn.close()

            # Parse response
            try:
                body_json = json.loads(body)
                status = body_json.get("status")

                if status == 20000000:
                    result = body_json.get("result", "")
                    logger.bind(tag=TAG).debug(f"Asr results: {result}")
                    return result
                else:
                    logger.bind(tag=TAG).error(f"Asr failed, status code: {status}")
                    return None

            except ValueError:
                logger.bind(tag=TAG).error("Response is not in json format")
                return None

        except Exception as e:
            logger.bind(tag=TAG).error(f"Asr request failed: {e}", exc_info=True)
            return None

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, audio_format="opus"
    ) -> Tuple[Optional[str], Optional[str]]:
        """Convert voice data to text"""
        if self._is_token_expired():
            logger.warning("Token has expired and is being refreshed automatically...")
            self._refresh_token()

        file_path = None
        try:
            # Decode opus to pcm
            if audio_format == "pcm":
                pcm_data = opus_data
            else:
                pcm_data = self.decode_opus(opus_data)
            combined_pcm_data = b"".join(pcm_data)

            # Determine whether to save as wav fileether to save as wav file
            if self.delete_audio_file:
                pass
            else:
                file_path = self.save_audio_to_file(pcm_data, session_id)

            # Send request and get text
            text = await self._send_request(combined_pcm_data)

            if text:
                return text, file_path

            return "", file_path

        except Exception as e:
            logger.bind(tag=TAG).error(f"Voice recognition failed: {e}", exc_info=True)
            return "", file_path
