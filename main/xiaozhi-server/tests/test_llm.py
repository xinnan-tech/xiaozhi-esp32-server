"""LLM link test.

Mock mode (default): Fetch config from data/.config.yaml to construct a real provider,
Network calls use the shim injected by conftest - no requests are sent.
Live mode (``RUN_LIVE_API_TESTS=1``): Calls real LLM provider, see
``performance_tester_llm.py`` ThreadPoolExecutor + 10s timeout pattern.

Interface contract (core/providers/llm/base.py):
    response(session_id, dialogue) -> Iterator[str], synchronous streaming generator
    response_no_stream(system_prompt, user_content) -> str

Special handling:
- Ollama requires model_name + local service availability
- placeholder detection ("Your" / "placeholder" / "xxx" / "sk-xxx")
- Since the LLM is a synchronous generator, it cannot directly use asyncio.wait_for -> use a thread pool
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
        pytest.skip("selected_module.LLM not set")
    cfg = get_provider_config("LLM", name)
    if not cfg:
        pytest.skip(f"LLM provider '{name}' configuration missing")

    # In any mode: if key is a placeholder, skip. Real requests require a real key; in mock mode
    # Running without a real key will cause errors in the real SDK network stack (openai/edge_tts).
    if name == "Ollama":
        if not cfg.get("model_name"):
            pytest.skip("model_name for LLM 'Ollama' is not configured")
    elif not has_real_key(cfg, "api_key"):
        if LIVE_API_TESTS:
            pytest.skip(f"api_key for LLM '{name}' not configured")
        else:
            pytest.skip(
                f"The api_key for LLM '{name}' is a placeholder (mock mode does not send real requests)."
                "Live request mode: export RUN_LIVE_API_TESTS=1 and provide a real key before running."
            )

    ptype = get_provider_type("LLM", name)
    if not ptype:
        pytest.skip(f"Missing type field for LLM '{name}'")
    from core.utils.llm import create_instance

    return create_instance(ptype, cfg)


def _collect_with_timeout(provider, session_id: str, dialogue, timeout: float = 10.0):
    """Call sync generator response() with thread pool and 10s timeout."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: list(provider.response(session_id, dialogue)))
        return future.result(timeout=timeout)


def test_llm_response_streams_non_empty() -> None:
    """response(session_id, dialogue) must produce a non-empty token stream."""
    provider = _build_provider()
    dialogue = [
        {"role": "system", "content": "You are an assistant"},
        {"role": "user", "content": "Say hi in one sentence"},
    ]
    chunks = _collect_with_timeout(provider, "test-session", dialogue, timeout=10.0)

    full = "".join(chunks).strip()
    assert isinstance(full, str), f"LLM chunks join should be str, got {type(full).__name__}"
    assert full, f"LLM returned empty response (provider={type(provider).__name__})"


def test_llm_response_no_stream_returns_string() -> None:
    """response_no_stream must return a non-empty string."""
    provider = _build_provider()
    text = provider.response_no_stream("You are an assistant", "Introduce Beijing").strip()

    assert isinstance(text, str), f"response_no_stream should return str, got {type(text).__name__}"
    assert text, "response_no_stream returns an empty string"


def test_llm_dialogue_min_length_one_user() -> None:
    """At least one user message dialogue should run successfully."""
    provider = _build_provider()
    dialogue = [{"role": "user", "content": "ping"}]
    chunks = _collect_with_timeout(provider, "s1", dialogue, timeout=10.0)

    assert "".join(chunks).strip(), "Single user message should return content"
