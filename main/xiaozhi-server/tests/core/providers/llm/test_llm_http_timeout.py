"""LLM provider 的 HTTP 超时与流式解析健壮性测试。

覆盖的问题：
- #1229 dify 对话一直「服务无响应」：provider 发请求没设 timeout，
  上游不响应时请求会一直挂着。
- #1560 接入 homeassistant 经常无响应：同上。

同时覆盖 dify 流式解析的两个健壮性问题：
- mode 配错时 request_json 未赋值，直接抛 UnboundLocalError；
- SSE 里出现一条解析不了的数据时，整段回复直接中断。
"""

import pytest
import requests

from core.providers.llm.base import LLMProviderBase
from core.providers.llm.dify import dify as dify_module
from core.providers.llm.dify.dify import LLMProvider as DifyProvider
from core.providers.llm.fastgpt.fastgpt import LLMProvider as FastGPTProvider
from core.providers.llm.homeassistant.homeassistant import (
    LLMProvider as HomeAssistantProvider,
)


class FakeResponse:
    """最小可用的 requests 响应替身"""

    def __init__(self, lines=None, payload=None):
        self._lines = lines or []
        self._payload = payload if payload is not None else {}

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def iter_lines(self):
        return iter(self._lines)

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


# ---------------------------------------------------------------- 超时解析


def test_resolve_timeout_uses_defaults():
    assert LLMProviderBase.resolve_timeout({}) == (10.0, 60.0)


def test_resolve_timeout_reads_config():
    config = {"timeout": 5, "connect_timeout": 2}
    assert LLMProviderBase.resolve_timeout(config) == (2.0, 5.0)


def test_resolve_timeout_falls_back_on_invalid_values():
    config = {"timeout": "abc", "connect_timeout": -1}
    assert LLMProviderBase.resolve_timeout(config) == (10.0, 60.0)


def test_resolve_timeout_handles_non_dict_config():
    assert LLMProviderBase.resolve_timeout(None) == (10.0, 60.0)


def test_resolve_timeout_accepts_custom_default():
    assert LLMProviderBase.resolve_timeout({}, default=30) == (10.0, 30.0)


# ---------------------------------------------------------------- dify


def _dify_config(**kwargs):
    config = {
        "api_key": "app-test-key",
        "base_url": "https://dify.example.com/v1",
        "mode": "chat-messages",
    }
    config.update(kwargs)
    return config


def test_dify_request_carries_timeout(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse(lines=[b'data: {"answer": "hi"}'])

    monkeypatch.setattr(dify_module.requests, "post", fake_post)

    provider = DifyProvider(_dify_config())
    result = list(provider.response("s1", [{"role": "user", "content": "你好"}]))
    assert result == ["hi"]
    assert captured["timeout"] == (10.0, 60.0)


def test_dify_timeout_is_configurable(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured.update(kwargs)
        return FakeResponse(lines=[b'data: {"answer": "hi"}'])

    monkeypatch.setattr(dify_module.requests, "post", fake_post)

    provider = DifyProvider(_dify_config(timeout=15, connect_timeout=3))
    list(provider.response("s1", [{"role": "user", "content": "你好"}]))
    assert captured["timeout"] == (3.0, 15.0)


def test_dify_read_timeout_is_propagated(monkeypatch):
    def fake_post(url, **kwargs):
        raise requests.exceptions.ReadTimeout("read timed out")

    monkeypatch.setattr(dify_module.requests, "post", fake_post)

    provider = DifyProvider(_dify_config())
    with pytest.raises(requests.exceptions.Timeout):
        list(provider.response("s1", [{"role": "user", "content": "你好"}]))


def test_dify_unknown_mode_raises_clear_error():
    provider = DifyProvider(_dify_config(mode="unknown-mode"))
    with pytest.raises(ValueError) as excinfo:
        list(provider.response("s1", [{"role": "user", "content": "你好"}]))
    assert "unknown-mode" in str(excinfo.value)


def test_dify_without_user_message_raises_clear_error():
    provider = DifyProvider(_dify_config())
    with pytest.raises(ValueError):
        list(provider.response("s1", [{"role": "assistant", "content": "你好"}]))


def test_dify_skips_unparsable_sse_line(monkeypatch):
    lines = [
        b"data: {not json",
        b"data: ",
        'data: {"answer": "世界"}'.encode("utf-8"),
    ]

    def fake_post(url, **kwargs):
        return FakeResponse(lines=lines)

    monkeypatch.setattr(dify_module.requests, "post", fake_post)

    provider = DifyProvider(_dify_config())
    result = list(provider.response("s1", [{"role": "user", "content": "你好"}]))
    assert result == ["世界"]


def test_dify_remembers_conversation_id(monkeypatch):
    lines = [b'data: {"conversation_id": "conv-1", "answer": "hi"}']

    def fake_post(url, **kwargs):
        return FakeResponse(lines=lines)

    monkeypatch.setattr(dify_module.requests, "post", fake_post)

    provider = DifyProvider(_dify_config())
    list(provider.response("s1", [{"role": "user", "content": "你好"}]))
    assert provider.session_conversation_map["s1"] == "conv-1"


# ---------------------------------------------------------------- fastgpt


def test_fastgpt_request_carries_timeout(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured.update(kwargs)
        return FakeResponse(
            lines=[b'data: {"choices": [{"delta": {"content": "hi"}}]}']
        )

    monkeypatch.setattr("core.providers.llm.fastgpt.fastgpt.requests.post", fake_post)

    provider = FastGPTProvider(
        {"api_key": "k", "base_url": "https://fastgpt.example.com"}
    )
    result = list(provider.response("s1", [{"role": "user", "content": "你好"}]))
    assert result == ["hi"]
    assert captured["timeout"] == (10.0, 60.0)


# ---------------------------------------------------------------- homeassistant


def test_homeassistant_request_carries_timeout(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured.update(kwargs)
        return FakeResponse(
            payload={"response": {"speech": {"plain": {"speech": "hello"}}}}
        )

    monkeypatch.setattr(
        "core.providers.llm.homeassistant.homeassistant.requests.post", fake_post
    )

    provider = HomeAssistantProvider(
        {"api_key": "k", "base_url": "http://ha.local:8123", "agent_id": "a1"}
    )
    result = list(provider.response("s1", [{"role": "user", "content": "开灯"}]))
    assert result == ["hello"]
    assert captured["timeout"] == (10.0, 60.0)


# ---------------------------------------------------------------- gemini


def test_gemini_proxy_probe_has_timeout(monkeypatch):
    gemini_module = pytest.importorskip("core.providers.llm.gemini.gemini")
    captured = {}

    class FakeGetResponse:
        status_code = 200

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return FakeGetResponse()

    monkeypatch.setattr(gemini_module.requests, "get", fake_get)

    assert gemini_module.test_proxy("http://proxy.local:7890", "http://example.com")
    assert captured["timeout"] == 10
