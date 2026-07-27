import base64
import hashlib
import hmac
import json
import re
from config.logger import setup_logging

logger = setup_logging()
TAG = __name__

_MAC_ADDRESS_PATTERN = re.compile(r"^(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")
_ENDPOINT_SCHEME_PATTERN = re.compile(
    r"^(?:mqtt|tcp|ssl|ws|wss|http|https)://", re.IGNORECASE
)


def normalize_signature_key(secret_key: str) -> str:
    """Treat values emitted by manager-api for an unset parameter as empty."""
    if secret_key is None:
        return ""
    value = str(secret_key).strip()
    if not value or value.lower() == "null" or "你" in value:
        return ""
    return value


def generate_password_signature(content: str, secret_key: str) -> str:
    """生成MQTT密码签名（HMAC-SHA256 + Base64）"""
    try:
        hmac_obj = hmac.new(
            secret_key.encode("utf-8"), content.encode("utf-8"), hashlib.sha256
        )
        signature = hmac_obj.digest()
        return base64.b64encode(signature).decode("utf-8")
    except Exception as e:
        logger.bind(tag=TAG).error(f"生成MQTT密码签名失败: {e}")
        return ""


def parse_mqtt_endpoint(endpoint: str, default_port: int = None) -> tuple[str, int]:
    """Parse the host[:port] syntax supported by the current ESP firmware."""
    if endpoint is None:
        return "", default_port
    value = str(endpoint).strip()
    if not value or value.lower() == "null" or "你" in value:
        return "", default_port

    value = _ENDPOINT_SCHEME_PATTERN.sub("", value, count=1).split("/", 1)[0]
    if not value or value.startswith("[") or value.count(":") > 1:
        raise ValueError("MQTT endpoint格式无效")

    host = value
    port = default_port
    if ":" in value:
        host, port_text = value.rsplit(":", 1)
        if not port_text.isdigit():
            raise ValueError("MQTT endpoint端口无效")
        port = int(port_text)

    if not host or any(char.isspace() for char in host):
        raise ValueError("MQTT endpoint主机无效")
    if port is not None and not 1 <= int(port) <= 65535:
        raise ValueError("MQTT endpoint端口超出范围")
    return host, int(port) if port is not None else None


def validate_mqtt_credentials(
    client_id: str, username: str, password: str, secret_key: str
) -> None:
    """Validate the gateway-compatible MQTT client id and HMAC credentials."""
    if not client_id or not isinstance(client_id, str):
        raise ValueError("clientId必须是非空字符串")

    parts = client_id.split("@@@")
    if len(parts) not in (2, 3) or not parts[0] or not parts[1]:
        raise ValueError("clientId格式错误")

    mac_address = parts[1].replace("_", ":")
    if not _MAC_ADDRESS_PATTERN.fullmatch(mac_address):
        raise ValueError("clientId中的MAC地址无效")

    normalized_key = normalize_signature_key(secret_key)
    if len(parts) == 2:
        if normalized_key:
            raise ValueError("启用签名时clientId必须包含UUID")
        return

    if not username or not isinstance(username, str):
        raise ValueError("username必须是非空字符串")
    try:
        user_data = json.loads(base64.b64decode(username, validate=True).decode("utf-8"))
        if not isinstance(user_data, dict):
            raise ValueError
    except Exception as exc:
        raise ValueError("username不是有效的base64编码JSON") from exc

    if normalized_key:
        expected = generate_password_signature(client_id + "|" + username, normalized_key)
        if not password or not hmac.compare_digest(password, expected):
            raise ValueError("密码签名验证失败")
