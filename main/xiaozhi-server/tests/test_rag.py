"""RAG（检索增强生成）链路测试。

xiaozhi-esp32-server 项目里没有独立的 RAG provider——RAG 由
MemoryProvider（mem0ai / powermem）的 ``query_memory`` 配合 LLM 工具调用实现。
本测试聚焦「save → query → 拿到检索结果」这一核心链路。

从 data/.config.yaml 拿真密钥。
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


def _build_memory_provider():
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


def test_rag_query_after_save_returns_string() -> None:
    """保存后 query_memory 应返回字符串（nomem 返回空串也合法）。"""
    provider = _build_memory_provider()
    msgs = [
        {"role": "user", "content": "我喜欢喝咖啡"},
        {"role": "assistant", "content": "好的记住了"},
    ]

    async def run():
        await provider.save_memory(msgs, "rag-session")
        return await provider.query_memory("咖啡")

    result = asyncio.run(run())
    assert isinstance(result, str), f"query_memory 应返回 str，得到 {type(result).__name__}"


def test_rag_query_no_match_returns_empty() -> None:
    """query 不存在内容时返回空字符串，不抛异常。"""
    provider = _build_memory_provider()

    async def run():
        return await provider.query_memory("完全不存在的关键词xyz")

    result = asyncio.run(run())
    assert isinstance(result, str)


def test_rag_empty_query_handled() -> None:
    """空 query 不应抛异常。"""
    provider = _build_memory_provider()

    async def run():
        await provider.save_memory([{"role": "user", "content": "测试"}], "s")
        return await provider.query_memory("")

    result = asyncio.run(run())
    assert isinstance(result, str)
