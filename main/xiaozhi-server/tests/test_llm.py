"""LLM 链路测试。

Mock 模式（默认）：从 data/.config.yaml 拿配置构造真实 provider，
网络调用走 conftest 注入的 shim —— 不发任何请求。
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
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _build_provider():
    name = get_selected_provider_name("LLM")
    if not name:
        pytest.skip("selected_module.LLM 未设置")
    cfg = get_provider_config("LLM", name)
    if not cfg:
        pytest.skip(f"LLM provider '{name}' 配置缺失")

    # 任何模式下：key 是占位符 → skip。真请求需要真 key；mock 模式下
    # 没有真 key 跑下去也会撞真 SDK 的网络栈（openai/edge_tts）报错。
    if name == "CozeLLM":
        if any(x in cfg.get("bot_id", "") for x in ["你的"]) or any(
            x in cfg.get("user_id", "") for x in ["你的"]
        ):
            pytest.skip("LLM 'CozeLLM' 的 bot_id/user_id 未配置")
    elif name == "Ollama":
        if not cfg.get("model_name"):
            pytest.skip("LLM 'Ollama' 的 model_name 未配置")
    elif not has_real_key(cfg, "api_key"):
        if LIVE_API_TESTS:
            pytest.skip(f"LLM '{name}' 的 api_key 未配置")
        else:
            pytest.skip(
                f"LLM '{name}' 的 api_key 是占位符（mock 模式不会真发请求）。"
                "真请求模式：export RUN_LIVE_API_TESTS=1 并填真 key 后再跑。"
            )

    ptype = get_provider_type("LLM", name)
    if not ptype:
        pytest.skip(f"LLM '{name}' 的 type 字段缺失")
    from core.utils.llm import create_instance

    return create_instance(ptype, cfg)


def _collect_with_timeout(provider, session_id: str, dialogue, timeout: float = 10.0):
    """调同步 generator response()，用线程池加 10s 超时。"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: list(provider.response(session_id, dialogue)))
        return future.result(timeout=timeout)


def test_llm_response_streams_non_empty() -> None:
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


def test_llm_response_no_stream_returns_string() -> None:
    """response_no_stream 应返回非空字符串。"""
    provider = _build_provider()
    text = provider.response_no_stream("你是助手", "介绍一下北京").strip()

    assert isinstance(text, str), f"response_no_stream 应返回 str，得到 {type(text).__name__}"
    assert text, "response_no_stream 返回空字符串"


def test_llm_dialogue_min_length_one_user() -> None:
    """至少一条 user 消息的 dialogue 应能跑通。"""
    provider = _build_provider()
    dialogue = [{"role": "user", "content": "ping"}]
    chunks = _collect_with_timeout(provider, "s1", dialogue, timeout=10.0)

    assert "".join(chunks).strip(), "单 user 消息应返回内容"
