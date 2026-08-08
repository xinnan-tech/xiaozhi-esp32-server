"""Regression tests for ``<think>`` tag stripping in the OpenAI-compatible provider.

Reasoning models often emit both ``<think>`` and ``</think>`` in a single streamed
chunk. Before the fix, ``response()`` truncated ``content`` at ``<think>`` first and
then tested the *already-truncated* string for ``</think>`` — the closing tag was
gone, ``is_active`` was never restored, and the entire post-``</think>`` answer was
dropped. The fix tests both tags against the original chunk.

These tests bypass ``__init__`` (which would build a real OpenAI client) via
``object.__new__`` and feed a fake streaming response.

Self-contained: no conftest required.
"""

import pathlib
import sys
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core.providers.llm.openai.openai import LLMProvider  # noqa: E402


def _chunk(content):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


def _make_provider(chunks):
    # A generator stands in for the OpenAI stream: response() iterates it and then
    # calls .close() in a finally block, which generators support (a plain iterator
    # does not).
    def _stream(**kwargs):
        for chunk in chunks:
            yield chunk

    provider = object.__new__(LLMProvider)
    provider.model_name = "test-model"
    provider.base_url = "http://localhost/v1"
    provider.max_tokens = None
    provider.temperature = None
    provider.top_p = None
    provider.frequency_penalty = None
    provider.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=_stream))
    )
    return provider


def test_think_open_and_close_in_one_chunk_yields_answer():
    # Regression: both tags in one chunk previously silenced the whole answer.
    provider = _make_provider([_chunk("<think>reasoning</think>Hello")])
    assert "".join(provider.response("sid", [])) == "Hello"


def test_think_block_across_chunks_suppresses_reasoning_only():
    provider = _make_provider(
        [_chunk("<think>"), _chunk("secret"), _chunk("</think>"), _chunk("answer")]
    )
    assert "".join(provider.response("sid", [])) == "answer"


def test_plain_content_passes_through_unchanged():
    provider = _make_provider([_chunk("Hello "), _chunk("world")])
    assert "".join(provider.response("sid", [])) == "Hello world"
