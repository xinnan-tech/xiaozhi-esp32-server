"""Regression tests for the orphan tool-message guard in ``Dialogue.getMessages``.

A ``role="tool"`` message is only valid when a preceding assistant message issued
a matching ``tool_call`` (correlated by id). Some paths (e.g. the intent REQLLM
handler in ``core/handle/intentHandler.py``) inject a bare tool result via
``Message(role="tool", content=text)`` with no ``tool_call_id`` and no preceding
assistant ``tool_calls``. When that dialogue is later replayed to an OpenAI-compat
LLM endpoint, the endpoint derives ``function_response.name`` by matching the
``tool_call_id`` back to a ``function_call``; with no match the name is empty.
``gemini-2.5-flash`` tolerated it, but ``gemini-3.5-flash`` rejects the whole
request with HTTP 400 ``function_response.name: Name cannot be empty``, dropping
the turn to the "system is busy" fallback.

The fix demotes such orphans to a plain assistant context line while leaving valid
tool-call pairs (including empty-string ids that still match) untouched.

Self-contained: ``Dialogue`` has no heavy dependencies, so no conftest required.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core.utils.dialogue import Dialogue, Message  # noqa: E402


def _serialize(messages):
    d = Dialogue()
    for m in messages:
        d.put(m)
    return d.get_llm_dialogue_with_memory(None, None)


def test_orphan_tool_message_is_demoted():
    # Mirrors the intent REQLLM path: a bare tool result with no matching tool_call.
    out = _serialize(
        [
            Message(role="user", content="turn on the light"),
            Message(role="tool", content="ok"),
            Message(role="user", content="anything else?"),
        ]
    )
    # The orphan must NOT be emitted as a tool/function_response...
    assert all(m.get("role") != "tool" for m in out), out
    # ...but its content must be preserved (demoted, not dropped).
    assert any(m.get("content") == "ok" for m in out), out


def test_valid_tool_pair_is_preserved():
    # An assistant tool_call followed by its matching tool result stays a function_response.
    out = _serialize(
        [
            Message(role="user", content="turn on the light"),
            Message(
                role="assistant",
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "set_light", "arguments": "{}"},
                    }
                ],
            ),
            Message(role="tool", tool_call_id="call_1", content="ok"),
        ]
    )
    assert any(
        m.get("role") == "tool" and m.get("tool_call_id") == "call_1" for m in out
    ), out


def test_empty_string_ids_still_match():
    # OpenAI-compat streaming can yield empty tool-call ids; an empty id on both the
    # assistant tool_call and the tool result still correlates and must be preserved.
    out = _serialize(
        [
            Message(role="user", content="x"),
            Message(
                role="assistant",
                tool_calls=[
                    {
                        "id": "",
                        "type": "function",
                        "function": {"name": "f", "arguments": "{}"},
                    }
                ],
            ),
            Message(role="tool", tool_call_id="", content="ok"),
        ]
    )
    assert any(m.get("role") == "tool" for m in out), out
