"""Memory 链路测试。

Mock 模式（默认）：从 data/.config.yaml 拿配置构造真实 provider；外部
SDK 调用（mem0ai / powermem 客户端）走 shim，不会真发请求。
Live 模式（``RUN_LIVE_API_TESTS=1``）：调真实 Memory provider。

接口约定（core/providers/memory/base.py）：
    async save_memory(msgs, session_id=None) -> str
    async query_memory(query: str) -> str

默认 selected_module.Memory = nomem（不开启记忆，本地即可）。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from tests.conftest import (
    get_provider_config,
    get_provider_type,
    get_selected_provider_name,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _build_provider():
    name = get_selected_provider_name("Memory")
    if not name:
        pytest.skip("selected_module.Memory 未设置")
    cfg = get_provider_config("Memory", name)
    if not cfg:
        pytest.skip(f"Memory provider '{name}' 配置缺失")
    ptype = get_provider_type("Memory", name)
    if not ptype:
        pytest.skip(f"Memory '{name}' 的 type 字段缺失")
    from core.utils.memory import create_instance

    return create_instance(ptype, cfg, None)


def test_memory_provider_constructs_from_config() -> None:
    """从 config 应该能实例化出 MemoryProviderBase 子类。"""
    provider = _build_provider()
    from core.providers.memory.base import MemoryProviderBase

    assert isinstance(provider, MemoryProviderBase), (
        f"Memory provider 类型错：{type(provider).__name__}"
    )


def test_memory_provider_exposes_save_and_query() -> None:
    """provider 必须实现 save_memory / query_memory。"""
    provider = _build_provider()
    assert hasattr(provider, "save_memory"), (
        f"{type(provider).__name__} 缺少 save_memory 方法"
    )
    assert hasattr(provider, "query_memory"), (
        f"{type(provider).__name__} 缺少 query_memory 方法"
    )


def test_memory_save_and_query_roundtrip() -> None:
    """save 后 query 应该不抛异常；nomem 返回 None/空串都算通过。"""
    provider = _build_provider()
    msgs = [{"role": "user", "content": "test message"}]

    async def run():
        mid = await provider.save_memory(msgs, "test-session")
        result = await provider.query_memory("test")
        return mid, result

    mid, result = asyncio.run(run())
    # nomem 等"不开记忆"实现可能返回 None；真实记忆服务应返回 str ID
    assert mid is None or isinstance(mid, str), (
        f"save_memory 应返回 str 或 None，得到 {type(mid).__name__}"
    )
    assert isinstance(result, str), "query_memory 应返回 str"
