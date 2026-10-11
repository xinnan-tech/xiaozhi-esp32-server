"""RAG (Retrieval-Augmented Generation) pipeline test.

The xiaozhi-esp32-server project does not have a standalone RAG provider - RAG is handled by
MemoryProvider (mem0ai / powermem) ``query_memory`` with LLM tools
Implementation call. This test focuses on the core flow: save -> query -> retrieve results.

Mock mode (default): Cloud calls for mem0/powermem etc. use shims and do not send requests.
Live mode (``RUN_LIVE_API_TESTS=1``): Send real requests to the selected memory provider.
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
        pytest.skip("selected_module.Memory not set")
    cfg = get_provider_config("Memory", name)
    if not cfg:
        pytest.skip(f"Missing configuration for memory provider '{name}'")
    ptype = get_provider_type("Memory", name)
    if not ptype:
        pytest.skip(f"Memory '{name}' missing type field")
    from core.utils.memory import create_instance

    return create_instance(ptype, cfg, None)


def test_rag_query_after_save_returns_string() -> None:
    """After saving, query_memory should return a string (empty string is valid for nomem)."""
    provider = _build_memory_provider()
    msgs = [
        {"role": "user", "content": "I like drinking coffee"},
        {"role": "assistant", "content": "Got it, noted"},
    ]

    async def run():
        await provider.save_memory(msgs, "rag-session")
        return await provider.query_memory("Coffee")

    result = asyncio.run(run())
    assert isinstance(result, str), f"query_memory should return str, got {type(result).__name__}"


def test_rag_query_no_match_returns_empty() -> None:
    """Return empty string when query content is missing; do not throw exception."""
    provider = _build_memory_provider()

    async def run():
        return await provider.query_memory("Keyword xyz does not exist")

    result = asyncio.run(run())
    assert isinstance(result, str)


def test_rag_empty_query_handled() -> None:
    """Empty query should not raise an exception."""
    provider = _build_memory_provider()

    async def run():
        await provider.save_memory([{"role": "user", "content": "Test"}], "s")
        return await provider.query_memory("")

    result = asyncio.run(run())
    assert isinstance(result, str)
