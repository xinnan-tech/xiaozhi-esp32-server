"""Regression tests for the null tool-reply guard in ``_handle_function_result``.

When a tool result carries both ``response`` and ``result`` as ``None``,
``text`` is ``None``. Before the fix, that ``None`` was sent to TTS and written to
the dialogue as an assistant message (and ``text in streamed_text`` raised
``TypeError`` when ``streamed_text`` was non-empty). The fix guards the whole
RESPONSE/NOTFOUND/ERROR branch on ``if text:``.

``ConnectionHandler`` is instantiated via ``object.__new__`` to bypass its heavy
``__init__``; only the attributes the method touches are populated.

Self-contained: no conftest required.
"""

import pathlib
import sys
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core.connection import ConnectionHandler  # noqa: E402
from plugins_func.register import Action  # noqa: E402


class _Logger:
    def bind(self, **kwargs):
        return self

    def debug(self, *args, **kwargs):
        pass


class _RecordingTTS:
    def __init__(self):
        self.sentences = []

    def tts_one_sentence(self, conn, content_type, content_detail=None):
        self.sentences.append(content_detail)

    def store_tts_text(self, sentence_id, text):
        pass


class _RecordingDialogue:
    def __init__(self):
        self.puts = []

    def put(self, message):
        self.puts.append(message)


def _make_conn():
    conn = object.__new__(ConnectionHandler)
    conn.logger = _Logger()
    conn.tts = _RecordingTTS()
    conn.dialogue = _RecordingDialogue()
    conn.sentence_id = "sid"
    return conn


_TOOL = {"name": "t", "id": "1", "arguments": ""}


def test_null_tool_reply_is_not_recorded():
    conn = _make_conn()
    result = SimpleNamespace(action=Action.RESPONSE, response=None, result=None)
    conn._handle_function_result([(result, _TOOL)], depth=0, streamed_text="")
    assert conn.dialogue.puts == []  # None reply must not reach the dialogue
    assert conn.tts.sentences == []  # nor TTS


def test_real_tool_reply_is_recorded():
    conn = _make_conn()
    result = SimpleNamespace(action=Action.RESPONSE, response="hello", result=None)
    conn._handle_function_result([(result, _TOOL)], depth=0, streamed_text="")
    assert len(conn.dialogue.puts) == 1
    assert conn.tts.sentences == ["hello"]
