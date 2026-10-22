import hmac
import base64
import hashlib
import time

DEFAULT_EXPIRE_SECONDS = 60 * 60 * 24 * 30
# 有效期上限，防止把过期时间配成准永久凭证
MAX_EXPIRE_SECONDS = 60 * 60 * 24 * 90


def normalize_expire_seconds(expire_seconds) -> int:
    """有效期归一化：非整数或非正数回落到默认值，超出上限则截断

    白名单设备的有效期是单独传的，走这里和构造时保持同一套规则，
    否则配成 0 会让 token 一秒就失效，配成字符串则会被当成校验失败
    """
    try:
        value = int(expire_seconds)
    except (TypeError, ValueError):
        return DEFAULT_EXPIRE_SECONDS
    if value <= 0:
        return DEFAULT_EXPIRE_SECONDS
    return min(value, MAX_EXPIRE_SECONDS)


def normalize_issued_after(issued_after) -> int:
    """吊销时刻归一化，配置不合法时直接报错，不留到验签时静默失败"""
    try:
        value = int(issued_after or 0)
    except (TypeError, ValueError):
        raise ValueError(f"server.auth.issued_after 必须是整数，当前值：{issued_after!r}")
    if value < 0:
        raise ValueError(f"server.auth.issued_after 不能为负数，当前值：{value}")
    if value > int(time.time()):
        raise ValueError(
            "server.auth.issued_after 是吊销线，只能是过去或当前的时间戳，"
            f"当前值：{value}"
        )
    return value


class AuthenticationError(Exception):
    """认证异常"""

    pass


class AuthManager:
    """
    统一授权认证管理器
    生成与验证 client_id device_id token（HMAC-SHA256）认证三元组
    token 中不含明文 client_id/device_id，只携带签名 + 时间戳; client_id/device_id在连接时传递
    在 MQTT 中 client_id: client_id, username: device_id, password: token
    在 Websocket 中，header:{Device-ID: device_id, Client-ID: client_id, Authorization: Bearer token, ......}
    """

    def __init__(
        self,
        secret_key: str,
        expire_seconds: int = DEFAULT_EXPIRE_SECONDS,
        issued_after: int = 0,
    ):
        self.expire_seconds = normalize_expire_seconds(expire_seconds)
        self.secret_key = secret_key
        self.issued_after = normalize_issued_after(issued_after)

    def _sign(self, content: str) -> str:
        """HMAC-SHA256签名并Base64编码"""
        sig = hmac.new(
            self.secret_key.encode("utf-8"), content.encode("utf-8"), hashlib.sha256
        ).digest()
        return base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")

    def generate_token(self, client_id: str, username: str) -> str:
        """
        生成 token
        Args:
            client_id: 设备连接ID
            username: 设备用户名（通常为deviceId）
        Returns:
            str: token字符串
        """
        ts = int(time.time())
        content = f"{client_id}|{username}|{ts}"
        signature = self._sign(content)
        # token仅包含签名与时间戳，不包含明文信息
        token = f"{signature}.{ts}"
        return token

    def verify_token(
        self,
        token: str,
        client_id: str,
        username: str,
        expire_seconds: int | None = None,
    ) -> bool:
        """
        验证token有效性
        Args:
            token: 客户端传入的token
            client_id: 连接使用的client_id
            username: 连接使用的username
            expire_seconds: 本次校验采用的过期时长，不传时用实例默认值
        """
        expire = (
            self.expire_seconds
            if expire_seconds is None
            else normalize_expire_seconds(expire_seconds)
        )
        try:
            sig_part, ts_str = token.split(".")
            ts = int(ts_str)
            if ts < self.issued_after:
                return False  # 签发时刻早于吊销线
            if int(time.time()) - ts > expire:
                return False  # 过期

            expected_sig = self._sign(f"{client_id}|{username}|{ts}")
            if not hmac.compare_digest(sig_part, expected_sig):
                return False

            return True
        except Exception:
            return False
