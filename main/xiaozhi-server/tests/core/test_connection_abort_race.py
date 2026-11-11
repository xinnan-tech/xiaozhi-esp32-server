"""确定时序的取消/换轮回归；驱动真实 chat，不连接模型或音频设备。"""
from __future__ import annotations

import queue
from types import SimpleNamespace

import pytest

from core.connection import ConnectionHandler
from core.utils.dialogue import Dialogue, Message


class _FakeLogger:
    """只实现 chat() 用到的日志接口。"""

    def bind(self, **_kwargs):
        return self

    def _noop(self, *_args, **_kwargs):
        return None

    info = debug = warning = error = _noop


class _FakeTTS:
    """收集 chat() 投递到 TTS 文本队列的内容。"""

    def __init__(self):
        self.tts_text_queue = queue.Queue()
        self.stored_text = {}

    def store_tts_text(self, sentence_id, text):
        self.stored_text[sentence_id] = text


class _FakeLLM:
    """按顺序吐出分片；abort_at 指定在第几个分片前模拟一次"迟到的打断"。"""

    def __init__(self, conn, chunks, abort_at=None):
        self.conn = conn
        self.chunks = chunks
        self.abort_at = abort_at

    def response(self, session_id, dialogue, **kwargs):
        for index, chunk in enumerate(self.chunks):
            if self.abort_at is not None and index == self.abort_at:
                # 模拟 abortHandle.handleAbortMessage() 在本轮流式期间到达
                self.conn.client_abort = True
            yield chunk


def _make_conn(chunks, abort_at=None, stale_abort=False):
    """构造一个只具备 chat() 所需属性的连接对象（不跑 __init__）。"""
    conn = ConnectionHandler.__new__(ConnectionHandler)
    conn.logger = _FakeLogger()
    conn.tts = _FakeTTS()
    conn.dialogue = Dialogue()
    conn.dialogue.put(Message(role="system", content="你是小智。"))
    conn.config = {}
    conn.session_id = "test-session"
    conn.sentence_id = "previous-turn-sentence"  # 上一轮的句子
    conn.intent_type = "intent_llm"  # 走普通（非 function_call）分支
    conn.memory = None
    conn.features = {"emoji": False}  # 跳过情绪识别（需要事件循环）
    conn.current_speaker = None
    conn.system_introduced_speakers = set()
    conn.llm = _FakeLLM(conn, chunks, abort_at)
    conn.client_abort = stale_abort
    return conn


def _sent_texts(conn):
    """取出投递给 TTS 的 TEXT 内容（忽略 FIRST/LAST 这类 ACTION 占位消息）。"""
    texts = []
    while not conn.tts.tts_text_queue.empty():
        item = conn.tts.tts_text_queue.get_nowait()
        if getattr(item, "content_detail", None):
            texts.append(item.content_detail)
    return texts


def test_chat_does_not_clear_abort():
    """chat 无法判断 abort 归属，必须尊重取消；仅新轮入口清理。"""
    conn = _make_conn(["第一句。", "第二句。"], stale_abort=True)

    assert ConnectionHandler.chat(conn, "念一首诗") is True
    assert conn.client_abort is True
    assert _sent_texts(conn) == []


def test_abort_during_current_stream_still_interrupts():
    """本轮流式期间新产生的 abort 仍要即时打断。"""
    conn = _make_conn(["第一句。", "第二句。", "第三句。"], abort_at=1)

    assert ConnectionHandler.chat(conn, "念一首诗") is True
    assert _sent_texts(conn) == ["第一句。"]


def test_no_abort_delivers_whole_answer():
    """没有任何打断时，全部分片都要投递给 TTS。"""
    conn = _make_conn(["一", "二", "三"])

    assert ConnectionHandler.chat(conn, "数数") is True
    assert _sent_texts(conn) == ["一", "二", "三"]


@pytest.mark.parametrize("replace_turn", [False, True])
def test_cancellation_before_first_chunk_closes_stream_without_history_or_last(replace_turn):
    conn = _make_conn([])
    closed = []

    def response(*args, **kwargs):
        try:
            if replace_turn:
                conn.sentence_id = "new-turn"
            else:
                conn.client_abort = True
            yield "不能播报"
        finally:
            closed.append(True)

    conn.llm.response = response
    assert conn.chat("旧问题") is True
    assert closed == [True]
    items = list(conn.tts.tts_text_queue.queue)
    assert len(items) == 1  # 只有生成前的 FIRST，没有 TEXT/LAST
    assert not conn.tts.stored_text
    assert all(m["role"] != "assistant" for m in conn.dialogue.get_llm_dialogue())


def test_cancel_during_memory_wait_is_preserved(monkeypatch):
    conn = _make_conn(["不能复活"])
    conn.memory = SimpleNamespace(query_memory=lambda query: None)
    conn.loop = None

    def result():
        conn.client_abort = True
        return "memory"

    monkeypatch.setattr("core.connection.asyncio.run_coroutine_threadsafe",
                        lambda *args: SimpleNamespace(result=result))
    assert conn.chat("问题") is True
    assert conn.client_abort is True
    assert _sent_texts(conn) == []


def test_delayed_old_worker_cannot_claim_new_turn():
    conn = _make_conn(["新回答"])
    conn.sentence_id = "new-turn"
    assert conn.chat("旧问题", current_sentence_id="old-turn") is True
    assert conn.sentence_id == "new-turn"
    assert conn.tts.tts_text_queue.empty()
    assert conn.chat("新问题", current_sentence_id="new-turn") is True
    assert _sent_texts(conn) == ["新回答"]


def test_old_worker_cannot_clear_new_turn_abort():
    conn = _make_conn(["不能复活"], stale_abort=True)
    conn.sentence_id = "new-turn"
    assert conn.chat("旧问题", current_sentence_id="old-turn") is True
    assert conn.client_abort is True
    assert conn.sentence_id == "new-turn"
    assert conn.tts.tts_text_queue.empty()


def test_audio_entry_assigns_turn_before_submitting_worker(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock, Mock
    from core.handle import receiveAudioHandle

    conn = _make_conn(["新回答"], stale_abort=True)
    conn.need_bind = False
    conn.max_output_size = 0
    conn.client_is_speaking = False
    conn.executor = SimpleNamespace(submit=Mock())
    monkeypatch.setattr(receiveAudioHandle, "handle_user_intent", AsyncMock(return_value=False))
    monkeypatch.setattr(receiveAudioHandle, "send_stt_message", AsyncMock())
    asyncio.run(receiveAudioHandle.startToChat(conn, "新问题"))
    args, kwargs = conn.executor.submit.call_args
    assert kwargs["current_sentence_id"] == conn.sentence_id
    assert conn.client_abort is False
    args[0](args[1], **kwargs)
    assert _sent_texts(conn) == ["新回答"]


def test_recursive_chat_keeps_original_turn():
    conn = _make_conn(["不能回答"])
    conn.sentence_id = "new-turn"
    assert conn.chat(None, depth=1, current_sentence_id="old-turn") is True
    assert conn.sentence_id == "new-turn"
    assert conn.tts.tts_text_queue.empty()


def test_tool_continuation_passes_original_turn():
    from plugins_func.register import Action, ActionResponse

    conn = _make_conn([])
    conn.sentence_id = "original-turn"
    calls = []
    conn.chat = lambda *args, **kwargs: calls.append((args, kwargs))
    conn._handle_function_result(
        [(ActionResponse(action=Action.REQLLM, result="tool result"),
          {"id": "tool-id", "name": "tool", "arguments": "{}"})],
        depth=0, current_sentence_id="original-turn",
    )
    assert calls == [((None,), {"depth": 1, "current_sentence_id": "original-turn"})]


def test_stale_stream_error_is_silent():
    conn = _make_conn([])

    def response(*args, **kwargs):
        conn.sentence_id = "new-turn"
        raise RuntimeError("old stream failed")
        yield

    conn.llm.response = response
    assert conn.chat("旧问题") is True
    assert len(list(conn.tts.tts_text_queue.queue)) == 1
    assert _sent_texts(conn) == []


def test_cancelled_tool_call_is_not_dispatched():
    conn = _make_conn([])
    conn.intent_type = "function_call"
    conn.func_handler = SimpleNamespace(get_functions=lambda: [])

    def response(*args, **kwargs):
        yield '<tool_call>{"name":"dangerous","arguments":{}}', None
        conn.client_abort = True
        yield "", None

    conn.llm.response_with_functions = response
    assert conn.chat("调用工具") is True
    assert not conn.tts.stored_text


def test_cancel_callback_can_end_stream_without_yielding():
    conn = _make_conn([])
    conn.llm.supports_cancel_check = True
    closed = []

    def response(*args, cancel_check):
        conn.sentence_id = "new-turn"
        assert cancel_check()
        closed.append(True)
        return
        yield

    conn.llm.response = response
    assert conn.chat("旧问题") is True
    assert closed == [True]
    assert len(list(conn.tts.tts_text_queue.queue)) == 1
