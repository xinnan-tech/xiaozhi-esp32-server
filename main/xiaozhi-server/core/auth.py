import hmac
import base64
import hashlib
import re
import time

from loguru import logger

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
    """吊销时刻归一化

    非整数和负数直接报错——这两类是配错了，不会有人这么填。
    超前的时间戳只降级成警告并截到当前时间：这一格最容易踩的是跨主机时钟偏差，
    而吊销线超前本来就等于没设，不值得为它把整个进程拖到起不来。
    """
    try:
        value = int(issued_after or 0)
    except (TypeError, ValueError):
        raise ValueError(f"server.auth.issued_after 必须是整数，当前值：{issued_after!r}")
    if value < 0:
        raise ValueError(f"server.auth.issued_after 不能为负数，当前值：{value}")
    now = int(time.time())
    if value > now:
        logger.warning(
            f"server.auth.issued_after 填的是未来的时间戳（当前值 {value}，本机 {now}），"
            "已截到当前时间。吊销线超前等于没设，请检查两台机器的时钟是否对得上"
        )
        return now
    return value


class AuthenticationError(Exception):
    """认证异常"""

    pass


def normalize_device_id(device_id: str) -> str:
    """把 Device-Id 归一成去掉分隔符的小写

    白名单、激活码绑定、OTA 请求头三处都要用同一个值比较，
    同一台设备换个分隔符或大小写就会被一边认一边不认。
    """
    return re.sub(r"[:\-_]", "", device_id).lower()


def auth_config_list(auth_config: dict, key: str) -> list:
    """取 auth 段里的列表型配置，配成标量字符串时直接报错

    不校验的话 set("aa:bb:cc:dd:ee:ff") 会逐字符拆成 7 个元素，
    激活码字符串会被拆成十个单字符码，配了等于没配还看不出问题。
    """
    value = auth_config.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"server.auth.{key} 必须是列表，当前值：{value!r}")
    return value


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
