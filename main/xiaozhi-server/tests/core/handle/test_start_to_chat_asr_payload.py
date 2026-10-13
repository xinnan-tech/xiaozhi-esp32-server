"""startToChat must hand the recognized text, not the ASR JSON, to the LLM."""
import json
import logging
from types import SimpleNamespace

import pytest

import core.handle.receiveAudioHandle as receive


class _Executor:
    def __init__(self):
        self.calls = []

    def submit(self, fn, *args):
        self.calls.append(args)


def _conn():
    logger = logging.getLogger("test")
    return SimpleNamespace(
        logger=SimpleNamespace(bind=lambda **_: logger),
        introduced_speakers=set(),
        current_speaker=None,
        need_bind=False,
        max_output_size=0,
        client_is_speaking=False,
        client_listen_mode="auto",
        client_abort=True,
        executor=_Executor(),
        chat=lambda text: None,
    )


@pytest.fixture(autouse=True)
def _no_side_effects(monkeypatch):
    async def not_handled(conn, text):
        return False

    async def ignore(*args, **kwargs):
        return None

    monkeypatch.setattr(receive, "handle_user_intent", not_handled)
    monkeypatch.setattr(receive, "send_stt_message", ignore)


async def test_funasr_payload_without_speaker_passes_only_content():
    conn = _conn()
    payload = json.dumps({"content": "今日は寒いね。", "language": "ja", "emotion": "😶"}, ensure_ascii=False)

    await receive.startToChat(conn, payload)

    assert conn.executor.calls == [("今日は寒いね。",)]
    assert conn.current_speaker is None


async def test_first_speaker_payload_still_keeps_json_once():
    conn = _conn()
    payload = json.dumps({"speaker": "Alice", "content": "hello"}, ensure_ascii=False)

    await receive.startToChat(conn, payload)
    await receive.startToChat(conn, payload)

    assert conn.executor.calls == [(payload,), ("hello",)]
    assert conn.current_speaker == "Alice"


async def test_plain_text_is_unchanged():
    conn = _conn()

    await receive.startToChat(conn, "你好")

    assert conn.executor.calls == [("你好",)]
