"""端口配置为空时的兜底行为。

#1491：从智控台读配置时，本地 config 没写端口（或写成空串），
整段 server 配置会被空字符串覆盖，随后 int("") 让服务在启动阶段直接崩掉。
"""

import asyncio

import config.config_loader as config_loader
from config.config_loader import get_config_from_api_async
from core.utils.util import safe_int


# ---------------- safe_int ----------------


def test_safe_int_empty_string_uses_default():
    assert safe_int("", 8003) == 8003


def test_safe_int_none_uses_default():
    assert safe_int(None, 8000) == 8000


def test_safe_int_numeric_string():
    assert safe_int("8000", 8003) == 8000


def test_safe_int_int_value():
    assert safe_int(8000, 8003) == 8000


def test_safe_int_strips_whitespace():
    assert safe_int("  8000 ", 8003) == 8000


def test_safe_int_invalid_value_uses_default():
    assert safe_int("abc", 8003) == 8003


# ---------------- get_config_from_api_async 的 server 段合并 ----------------


def _local_config(server=None):
    """构造一份本地配置（data/.config.yaml 的形状）。"""
    config = {
        "manager-api": {"url": "http://127.0.0.1:8002/xiaozhi", "secret": "secret"},
    }
    if server is not None:
        config["server"] = server
    return config


def _run(monkeypatch, local_config, api_server):
    """跑一次 get_config_from_api_async，把 API 返回的 server 段替换成 api_server。"""

    async def fake_get_server_config():
        data = {"selected_module": {}}
        if api_server is not None:
            data["server"] = dict(api_server)
        return data

    monkeypatch.setattr(config_loader, "init_service", lambda config: None)
    monkeypatch.setattr(config_loader, "get_server_config", fake_get_server_config)
    return asyncio.run(get_config_from_api_async(local_config))


API_SERVER = {
    "ip": "0.0.0.0",
    "port": 8000,
    "http_port": 8003,
    "vision_explain": "http://127.0.0.1:8003/mcp/vision/explain",
}


def test_local_ports_win_over_api(monkeypatch):
    result = _run(
        monkeypatch,
        _local_config({"port": 9000, "http_port": 9001}),
        API_SERVER,
    )
    assert result["server"]["port"] == 9000
    assert result["server"]["http_port"] == 9001


def test_missing_local_ports_fall_back_to_api(monkeypatch):
    """本地 server 段没写端口时，不该把 API 下发的端口覆盖成空串。"""
    result = _run(monkeypatch, _local_config({"ip": "0.0.0.0"}), API_SERVER)
    assert result["server"]["port"] == 8000
    assert result["server"]["http_port"] == 8003


def test_empty_local_ports_fall_back_to_api(monkeypatch):
    """本地端口写成空串时，同样回退到 API 的值。"""
    result = _run(
        monkeypatch,
        _local_config({"port": "", "http_port": ""}),
        API_SERVER,
    )
    assert result["server"]["port"] == 8000
    assert result["server"]["http_port"] == 8003


def test_ports_fall_back_to_defaults_when_neither_side_has_them(monkeypatch):
    """两边都没有端口时，用默认值，而不是空字符串。"""
    result = _run(monkeypatch, _local_config({"ip": "0.0.0.0"}), {})
    assert result["server"]["port"] == 8000
    assert result["server"]["http_port"] == 8003


def test_local_ports_survive_when_api_has_no_server_section(monkeypatch):
    result = _run(monkeypatch, _local_config({"port": 9000}), None)
    assert result["server"]["port"] == 9000
    assert result["server"]["http_port"] == 8003


def test_other_api_server_fields_are_kept(monkeypatch):
    """智控台下发的其它 server 字段不再被整体覆盖掉。"""
    api_server = dict(API_SERVER)
    api_server["timezone_offset"] = 8
    api_server["websocket"] = "ws://127.0.0.1:8000/xiaozhi/v1/"
    result = _run(monkeypatch, _local_config({"port": 9000}), api_server)
    assert result["server"]["timezone_offset"] == 8
    assert result["server"]["websocket"] == "ws://127.0.0.1:8000/xiaozhi/v1/"


def test_auth_flag_is_preserved(monkeypatch):
    result = _run(monkeypatch, _local_config({"port": 9000}), API_SERVER)
    assert result["server"]["auth"] == {"enabled": False}
