"""回归测试：barge-in 打断后残留的 client_abort 会误断新一轮 LLM 流。

问题（issue #3437）：上一轮 TTS 播放被用户打断（barge-in）后，设备发来的 abort
消息可能在新一轮 LLM 流建立之后才到达 ``core/handle/abortHandle.py``，那里会把
``conn.client_abort`` 置为 True。而 ``core/handle/receiveAudioHandle.py`` 里的
清理发生在 ``conn.executor.submit(conn.chat, ...)`` 之前，于是这个"针对上一轮"
的标志会残留到新一轮的流式循环里：``chat()`` 在首个分片处 ``if self.client_abort:
break``，新一轮回答只播第一句（或完全没有声音），服务端没有任何报错。

本文件用最小限度的假连接对象直接驱动 ``ConnectionHandler.chat()``：不加载任何模型、
不连网络、不碰音频设备，只验证"进入流式循环前清理残留标志"这一行为。
"""
from __future__ import annotations

import queue

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


def test_stale_abort_from_previous_turn_does_not_kill_new_answer():
    """上一轮残留的 client_abort 不应让新一轮回答只剩第一句。"""
    conn = _make_conn(["第一句。", "第二句。"], stale_abort=True)

    assert ConnectionHandler.chat(conn, "念一首诗") is True
    assert _sent_texts(conn) == ["第一句。", "第二句。"]


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
