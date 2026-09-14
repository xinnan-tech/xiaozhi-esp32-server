"""LLM 链路测试。

从 data/.config.yaml 拿配置，调真实 LLM provider。

接口约定（core/providers/llm/base.py）：
    response(session_id, dialogue) -> Iterator[str]，同步流式生成器
    response_no_stream(system_prompt, user_content) -> str

参考项目自带的 performance_tester_llm.py 模式：
- 特殊处理 CozeLLM（看 bot_id / user_id 而非 api_key）
- 特殊处理 Ollama（要 model_name + 本地服务可用）
- placeholder 检测（"你的" / "placeholder" / "xxx" / "sk-xxx"）
- ThreadPoolExecutor + 10s 超时防卡死
- 因为 LLM 是同步 generator，不能直接 asyncio.wait_for，得用线程池

默认 selected_module.LLM = ChatGLMLLM（glm-4-flash 免费但要 key），
如果 data/.config.yaml 没填 api_key 则 skip。
"""
from __future__ import annotations

import concurrent.futures
import sys
from pathlib import Path

import pytest

from tests.conftest import (
    CONFIG,
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

    # 参考 performance_tester_llm.py：CozeLLM 看 bot_id/user_id 而非 api_key
    if name == "CozeLLM":
        if any(x in cfg.get("bot_id", "") for x in ["你的"]) or any(
            x in cfg.get("user_id", "") for x in ["你的"]
        ):
            pytest.skip(
                "LLM 'CozeLLM' 的 bot_id/user_id 未配置——"
                "请在 data/.config.yaml 的 LLM.CozeLLM.{bot_id,user_id} 填写真实值"
            )
    # Ollama 看 model_name 而不是 api_key（本地服务）
    elif name == "Ollama":
        if not cfg.get("model_name"):
            pytest.skip(
                "LLM 'Ollama' 的 model_name 未配置——"
                "请在 data/.config.yaml 的 LLM.Ollama.model_name 填写真实模型名"
            )
    # 其他 provider 看 api_key
    elif not has_real_key(cfg, "api_key"):
        pytest.skip(
            f"LLM '{name}' 的 api_key 未配置——"
            f"请在 data/.config.yaml 的 LLM.{name}.api_key 填写真实密钥"
        )

    ptype = get_provider_type("LLM", name)
    if not ptype:
        pytest.skip(f"LLM '{name}' 的 type 字段缺失")
    from core.utils.llm import create_instance

    return create_instance(ptype, cfg)


def _collect_with_timeout(provider, session_id: str, dialogue, timeout: float = 10.0):
    """调同步 generator response()，用线程池加 10s 超时。

    LLM.response() 是同步 generator，不是 async，没法直接 await。
    参考 performance_tester_llm.py 用 ThreadPoolExecutor + future.result(timeout)。
    """
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
