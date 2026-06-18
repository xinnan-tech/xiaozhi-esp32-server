"""Regression guard for bounded cross-thread ``future.result()`` calls.

Two ``future.result()`` calls previously had no timeout, so a stalled dependency
(a hung memory backend in ``connection.py``; a stalled WebSocket send in the TTS
audio thread in ``tts/base.py``) blocked the thread indefinitely. The fix added a
timeout plus a ``TimeoutError`` handler at both sites.

Those call sites live inside large methods / a queue-driven thread loop that can't
be exercised in isolation without a full runtime, so this is a structural guard:
it parses the source and asserts each file still contains a ``try`` block whose
body calls ``<future>.result(timeout=...)`` and whose ``except`` handles a
``*TimeoutError``. It fails if a refactor drops the timeout or the handler.

Self-contained: stdlib only, no conftest required.
"""

import ast
import pathlib

_SERVER_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _handler_names(handler):
    """Return the trailing identifier(s) of an except handler's exception type."""
    node = handler.type
    names = []
    if isinstance(node, ast.Tuple):
        candidates = node.elts
    elif node is not None:
        candidates = [node]
    else:
        candidates = []
    for cand in candidates:
        if isinstance(cand, ast.Name):
            names.append(cand.id)
        elif isinstance(cand, ast.Attribute):
            names.append(cand.attr)
    return names


def _is_timed_result_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "result"
        and any(kw.arg == "timeout" for kw in node.keywords)
    )


def _assigns_name(stmt):
    """Yield assignment target names for a simple ``name = ...`` statement."""
    if isinstance(stmt, ast.Assign):
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                yield target.id


def _try_body_has_timed_result(body, assign_target=None):
    for stmt in body:
        for node in ast.walk(stmt):
            if not _is_timed_result_call(node):
                continue
            if assign_target is None:
                return True
            # Require the timed result to be assigned to the named variable so the
            # guard targets a specific call site rather than any timed result call.
            if assign_target in set(_assigns_name(stmt)):
                return True
    return False


def _guards_a_timed_result_call(source, assign_target=None):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if not _try_body_has_timed_result(node.body, assign_target):
            continue
        for handler in node.handlers:
            if any(name.endswith("TimeoutError") for name in _handler_names(handler)):
                return True
    return False


def test_connection_memory_query_result_is_timeout_guarded():
    source = (_SERVER_ROOT / "core" / "connection.py").read_text(encoding="utf-8")
    # Target the memory-query site specifically (assigns to ``memory_str``); the
    # pre-existing tool-call timeout must not mask a regression here.
    assert _guards_a_timed_result_call(source, assign_target="memory_str"), (
        "connection.py must assign memory_str = future.result(timeout=...) inside a "
        "try/except that handles a TimeoutError"
    )


def test_tts_audio_send_result_is_timeout_guarded():
    source = (_SERVER_ROOT / "core" / "providers" / "tts" / "base.py").read_text(
        encoding="utf-8"
    )
    assert _guards_a_timed_result_call(source), (
        "tts/base.py must wrap a future.result(timeout=...) call in a try/except "
        "that handles a TimeoutError"
    )
