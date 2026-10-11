"""Memory link test.

Mock mode (default): get config from data/.config.yaml to construct real provider; external
SDK calls (mem0ai / powermem clients) use a shim and do not send real requests.
Live mode (``RUN_LIVE_API_TESTS=1``): calls real Memory provider.

API contract (core/providers/memory/base.py):
    async save_memory(msgs, session_id=None) -> str
    async query_memory(query: str) -> str

Default selected_module.Memory = nomem (memory disabled, local only).
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
        pytest.skip("selected_module.Memory not set")
    cfg = get_provider_config("Memory", name)
    if not cfg:
        pytest.skip(f"Missing configuration for memory provider '{name}'")
    ptype = get_provider_type("Memory", name)
    if not ptype:
        pytest.skip(f"Memory '{name}' missing type field")
    from core.utils.memory import create_instance

    return create_instance(ptype, cfg, None)


def test_memory_provider_constructs_from_config() -> None:
    """MemoryProviderBase subclasses should be instantiable from config."""
    provider = _build_provider()
    from core.providers.memory.base import MemoryProviderBase

    assert isinstance(provider, MemoryProviderBase), (
        f"Invalid Memory provider type: {type(provider).__name__}"
    )


def test_memory_provider_exposes_save_and_query() -> None:
    """Provider must implement save_memory / query_memory."""
    provider = _build_provider()
    assert hasattr(provider, "save_memory"), (
        f"{type(provider).__name__} missing save_memory method"
    )
    assert hasattr(provider, "query_memory"), (
        f"{type(provider).__name__} missing query_memory method"
    )


def test_memory_save_and_query_roundtrip() -> None:
    """Query after save should not throw exceptions; nomem returning None or empty string is considered passing."""
    provider = _build_provider()
    msgs = [{"role": "user", "content": "test message"}]

    async def run():
        mid = await provider.save_memory(msgs, "test-session")
        result = await provider.query_memory("test")
        return mid, result

    mid, result = asyncio.run(run())
    # Implementations like nomem that disable memory may return None; real memory services should return a str ID
    assert mid is None or isinstance(mid, str), (
        f"save_memory should return str or None, got {type(mid).__name__}"
    )
    assert isinstance(result, str), "query_memory should return str"
