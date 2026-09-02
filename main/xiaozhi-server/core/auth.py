import hmac
import base64
import hashlib
import time


class AuthenticationError(Exception):
    """Authentication Exception"""

    pass


class AuthManager:
    """
    Unified authorization authentication manager
    Generate and verify client_id device_id token (HMAC-SHA256) authentication triplet
    Token does not contain plaintext client_id/device_id, only carries signature + timestamp; client_id/device_id is passed during connection
    In MQTT: client_id: client_id, username: device_id, password: token
    In Websocket: header:{Device-ID: device_id, Client-ID: client_id, Authorization: Bearer token, ......}
    """

    def __init__(self, secret_key: str, expire_seconds: int = 60 * 60 * 24 * 30):
        if not expire_seconds or expire_seconds < 0:
            self.expire_seconds = 60 * 60 * 24 * 30
        else:
            self.expire_seconds = expire_seconds
        self.secret_key = secret_key

    def _sign(self, content: str) -> str:
        """HMAC-SHA256 signature and Base64 encoding"""
        sig = hmac.new(
            self.secret_key.encode("utf-8"), content.encode("utf-8"), hashlib.sha256
        ).digest()
        return base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")

    def generate_token(self, client_id: str, username: str) -> str:
        """
        Generate token
        Args:
            client_id: Device connection ID
            username: Device username (usually deviceId)
        Returns:
            str: token string
        """
        ts = int(time.time())
        content = f"{client_id}|{username}|{ts}"
        signature = self._sign(content)
        # token only contains signature and timestamp, no plaintext info
        token = f"{signature}.{ts}"
        return token

    def verify_token(self, token: str, client_id: str, username: str) -> bool:
        """
        Verify token validity
        Args:
            token: token passed by client
            client_id: client_id used for connection
            username: username used for connection
        """
        try:
            sig_part, ts_str = token.split(".")
            ts = int(ts_str)
            if int(time.time()) - ts > self.expire_seconds:
                return False  # Expired

            expected_sig = self._sign(f"{client_id}|{username}|{ts}")
            if not hmac.compare_digest(sig_part, expected_sig):
                return False

            return True
        except Exception:
            return False
