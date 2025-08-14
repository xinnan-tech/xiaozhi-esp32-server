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
        
        self.api_url = "https://tts.tencentcloudapi.com"  # Correct API endpoint
        self.region = config.get("region")
        self.output_file = config.get("output_dir")
        self.audio_file_type = config.get("format", "wav")
    
    def _get_auth_headers(self, request_body):
        """Generate authentication request headers"""
        # Get current UTC timestamp
        timestamp = int(time.time())
        
        # Calculate date using UTC time
        utc_date = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(
            "%Y-%m-%d"
        )
        
        # Service name must be "tts"
        service = "tts"
        
        # Construct credential scope
        credential_scope = f"{utc_date}/{service}/tc3_request"
        
        # Use TC3-HMAC-SHA256 signature method
        algorithm = "TC3-HMAC-SHA256"
        
        # Build canonical request string
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        
        # Request headers must include host and content-type, sorted in dictionary order
        canonical_headers = (
            f"content-type:application/json\n" f"host:tts.tencentcloudapi.com\n"
        )
        
        signed_headers = "content-type;host"
        
        # Request body hash value
        payload = json.dumps(request_body)
        payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        
        # Build canonical request string
        canonical_request = (
            f"{http_request_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )
        
        # Calculate hash value of canonical request
        hashed_canonical_request = hashlib.sha256(
            canonical_request.encode("utf-8")
        ).hexdigest()
        
        # Build string to sign
        string_to_sign = (
            f"{algorithm}\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{hashed_canonical_request}"
        )
        
        # Calculate signature key
        secret_date = self._hmac_sha256(
            f"TC3{self.secret_key}".encode("utf-8"), utc_date
        )
        secret_service = self._hmac_sha256(secret_date, service)
        secret_signing = self._hmac_sha256(secret_service, "tc3_request")
        
        # Calculate signature
        signature = hmac.new(
            secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        
        # Build authorization header
        authorization = (
            f"{algorithm} "
            f"Credential={self.secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )
        
        # Build request headers
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
        """HMAC-SHA256 encryption"""
        if isinstance(msg, str):
            msg = msg.encode("utf-8")
        return hmac.new(key, msg, hashlib.sha256).digest()
    
    async def text_to_speak(self, text, output_file):
        # Build request body
        request_json = {
            "Text": text,  # Source text for speech synthesis
            "SessionId": str(uuid.uuid4()),  # Session ID, randomly generated
            "VoiceType": int(self.voice),  # Voice type
        }
        
        try:
            # Get request headers (regenerate for each request to ensure timestamp and signature are up-to-date)
            headers = self._get_auth_headers(request_json)
            
            # Send request
            resp = requests.post(
                self.api_url, json.dumps(request_json), headers=headers
            )
            
            # Check response
            if resp.status_code == 200:
                response_data = resp.json()
                
                # Check if successful
                if response_data.get("Response", {}).get("Error") is not None:
                    error_info = response_data["Response"]["Error"]
                    raise Exception(
                        f"API returned error: {error_info['Code']}: {error_info['Message']}"
                    )
                
                # Decode Base64 audio data
                audio_bytes = base64.b64decode(response_data["Response"].get("Audio"))
                
                if audio_bytes:
                    if output_file:
                        with open(output_file, "wb") as f:
                            f.write(audio_bytes)
                    else:
                        return audio_bytes
                else:
                    raise Exception(f"{__name__}: No audio data returned: {response_data}")
            else:
                raise Exception(
                    f"{__name__} status_code: {resp.status_code} response: {resp.content}"
                )
        
        except Exception as e:
            raise Exception(f"{__name__} error: {e}")
