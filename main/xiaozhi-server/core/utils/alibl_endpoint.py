import re
from urllib.parse import urlsplit


DEFAULT_WS_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference/"
INFERENCE_PATH = "/api-ws/v1/inference"
HOSTNAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
HAPPY_EYEBALLS_DELAY = 0.25


def build_ws_connect_options(open_timeout):
    return {
        "open_timeout": open_timeout,
        "happy_eyeballs_delay": HAPPY_EYEBALLS_DELAY,
        "interleave": 1,
    }


def resolve_ws_url(value):
    ws_url = str(value or DEFAULT_WS_URL).strip()
    parsed = urlsplit(ws_url)
    hostname = (parsed.hostname or "").lower()
    is_dashscope = hostname in {
        "dashscope.aliyuncs.com",
        "dashscope-intl.aliyuncs.com",
    }
    is_workspace = hostname.endswith(".maas.aliyuncs.com")

    try:
        port = parsed.port
    except ValueError:
        port = -1

    if (
        parsed.scheme.lower() != "wss"
        or not HOSTNAME_PATTERN.fullmatch(hostname)
        or not (is_dashscope or is_workspace)
        or parsed.path.rstrip("/") != INFERENCE_PATH
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or port not in {None, 443}
    ):
        raise ValueError(
            "ws_url must be an official Alibaba Cloud WSS inference endpoint"
        )
    return ws_url
