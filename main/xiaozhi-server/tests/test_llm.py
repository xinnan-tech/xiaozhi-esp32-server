"""LLM 链路测试。

Mock 模式（默认）：从 data/.config.yaml 拿配置构造真实 provider，
网络那一段换成本文件里的假接口 —— provider 自己拼请求、自己解析
流式回应那套代码照跑，只是不发真请求，也不需要真 key。
Live 模式（``RUN_LIVE_API_TESTS=1``）：调真实 LLM provider，参考
``performance_tester_llm.py`` 的 ThreadPoolExecutor + 10s 超时模式。

接口约定（core/providers/llm/base.py）：
    response(session_id, dialogue) -> Iterator[str]，同步流式生成器
    response_no_stream(system_prompt, user_content) -> str

特殊处理：
- CozeLLM 看 bot_id / user_id 而非 api_key
- Ollama 要 model_name + 本地服务可用
- placeholder 检测（"你的" / "placeholder" / "xxx" / "sk-xxx"）
- 因为 LLM 是同步 generator，不能直接 asyncio.wait_for → 线程池
"""
from __future__ import annotations

import concurrent.futures
import json
import sys
from pathlib import Path

import pytest

from tests.conftest import (
    CONFIG,
    LIVE_API_TESTS,
    get_provider_config,
    get_provider_type,
    get_selected_provider_name,
    has_real_key,
    skip_or_fail,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 假接口回的固定内容。够长，能看出是流式拼出来的。
_MOCK_ANSWER = "这是 mock 出来的回应"


@pytest.fixture(autouse=True)
def _mock_chat_completions(monkeypatch):
    """Mock 模式下给 chat/completions 装一个假的回应。

    装在 httpx 这一层：provider 拼请求、走流式解析那套代码都是真的，
    只有网络那一段是假的。这样不用真 key 也能验证这条链路。

    发出去的请求体记在返回的列表里，用例要检查 provider 真的把这次对话
    装进了请求里。
    """
    if LIVE_API_TESTS:
        yield None
        return

    import httpx

    stream_body = (
        "data: "
        + json.dumps(
            {
                "id": "chatcmpl-mock",
                "object": "chat.completion.chunk",
                "created": 1700000000,
                "model": "mock-model",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": _MOCK_ANSWER},
                        "finish_reason": None,
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n\n"
        + "data: [DONE]\n\n"
    ).encode("utf-8")

    plain_body = json.dumps(
        {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 1700000000,
            "model": "mock-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": _MOCK_ANSWER},
                    "finish_reason": "stop",
                }
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")

    sent_requests = []

    def _fake_send(self, request, **kwargs):
        content = getattr(request, "content", b"") or b""
        sent_requests.append(content)
        if b'"stream":true' in content.replace(b" ", b""):
            payload = stream_body
            headers = {"content-type": "text/event-stream"}
        else:
            payload = plain_body
            headers = {"content-type": "application/json"}
        response = httpx.Response(200, content=payload, headers=headers)
        response.request = request
        return response

    monkeypatch.setattr(httpx.Client, "send", _fake_send)
    yield sent_requests


def _sent_body(requests):
    """最后一次发出去的请求体。live 模式没有假接口，返回 None"""
    if requests is None:
        return None
    assert requests, "provider 一次请求都没发出去"
    return json.loads(requests[-1].decode("utf-8"))


def _assert_request(body, provider, expected_contents):
    """检查请求体：模型名在、这次对话在

    <p>
    只看回应非空的话，provider 把消息丢掉、自己编一句话回来，测试照样绿。
    """
    if body is None:
        return
    assert body.get("model"), "请求里得带上模型名"
    expected_model = getattr(provider, "model_name", None)
    if expected_model:
        assert body["model"] == expected_model, "请求里的模型名跟配置对不上"
    messages = body.get("messages") or []
    assert messages, "请求里得带上对话"
    contents = [message.get("content") for message in messages]
    for text in expected_contents:
        assert text in contents, f"请求里没有把「{text}」发出去"


def _build_provider():
    name = get_selected_provider_name("LLM")
    if not name:
        skip_or_fail("selected_module.LLM 未设置")
    cfg = get_provider_config("LLM", name)
    if not cfg:
        skip_or_fail(f"LLM provider '{name}' 配置缺失")

    # 任何模式下：key 是占位符 → 真请求没法发。mock 模式有假接口顶上，
    # 但占位符本身是中文，httpx 拼 Authorization 头的时候会直接报编码错，
    # 所以 mock 模式把它换成一把假的 ascii key
    if name == "CozeLLM":
        if any(x in cfg.get("bot_id", "") for x in ["你的"]) or any(
            x in cfg.get("user_id", "") for x in ["你的"]
        ):
            skip_or_fail("LLM 'CozeLLM' 的 bot_id/user_id 未配置")
    elif name == "Ollama":
        if not cfg.get("model_name"):
            skip_or_fail("LLM 'Ollama' 的 model_name 未配置")
    elif not has_real_key(cfg, "api_key"):
        if LIVE_API_TESTS:
            skip_or_fail(f"LLM '{name}' 的 api_key 未配置")
        cfg = dict(cfg)
        cfg["api_key"] = "mock-api-key"

    ptype = get_provider_type("LLM", name)
    if not ptype:
        skip_or_fail(f"LLM '{name}' 的 type 字段缺失")
    from core.utils.llm import create_instance

    return create_instance(ptype, cfg)


def _collect_with_timeout(provider, session_id: str, dialogue, timeout: float = 10.0):
    """调同步 generator response()，用线程池加 10s 超时。"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: list(provider.response(session_id, dialogue)))
        return future.result(timeout=timeout)


def test_llm_response_streams_non_empty(_mock_chat_completions) -> None:
    """response(session_id, dialogue) 应产生非空 token 流。"""
    provider = _build_provider()
    dialogue = [
        {"role": "system", "content": "你是助手"},
        {"role": "user", "content": "用一句话说 hi"},
    ]
    chunks = _collect_with_timeout(provider, "test-session", dialogue, timeout=10.0)

    full = "".join(chunks).strip()
    assert isinstance(full, str), f"LLM chunks join 应是 str，得到 {type(full).__name__}"
    assert full, f"LLM 返回空响应（provider={type(provider).__name__}）"
    # 回的得是假接口给的那句，不是随便一个非空串
    assert full == _MOCK_ANSWER
    _assert_request(
        _sent_body(_mock_chat_completions),
        provider,
        ["你是助手", "用一句话说 hi"],
    )


def test_llm_response_no_stream_returns_string(_mock_chat_completions) -> None:
    """response_no_stream 应返回非空字符串。"""
    provider = _build_provider()
    text = provider.response_no_stream("你是助手", "介绍一下北京").strip()

    assert isinstance(text, str), f"response_no_stream 应返回 str，得到 {type(text).__name__}"
    assert text, "response_no_stream 返回空字符串"
    assert text == _MOCK_ANSWER
    _assert_request(
        _sent_body(_mock_chat_completions), provider, ["你是助手", "介绍一下北京"]
    )


def test_llm_dialogue_min_length_one_user(_mock_chat_completions) -> None:
    """至少一条 user 消息的 dialogue 应能跑通。"""
    provider = _build_provider()
    dialogue = [{"role": "user", "content": "ping"}]
    chunks = _collect_with_timeout(provider, "s1", dialogue, timeout=10.0)

    assert "".join(chunks).strip(), "单 user 消息应返回内容"
    _assert_request(_sent_body(_mock_chat_completions), provider, ["ping"])
