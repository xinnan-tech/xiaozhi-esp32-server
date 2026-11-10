"""意图识别漏召回时的知识库兜底检索测试。

复现场景（issue #3555）：知识库里明明有对应问答，但意图识别阶段
只凭"知识库名称+描述"判断相关性，描述没覆盖该细分主题时直接判为
不相关，检索根本没被触发。

覆盖点：
1. ``retrieve_chunks`` 按相似度过滤并按降序返回；
2. 命中阈值时 ``fallback_knowledge_base`` 接管本轮回答；
3. 未命中 / 关闭开关 / 未配置知识库时，行为与改动前一致（返回 False）。
"""
from __future__ import annotations

import asyncio
import json
import threading
import types
from concurrent.futures import ThreadPoolExecutor

import httpx

from config.logger import setup_logging

# 模块级初始化：setup_logging 内部会用 asyncio.run 读配置，
# 不能在事件循环里首次调用，否则会撞上 "asyncio.run() cannot be called from a running event loop"
LOGGER = setup_logging()

CHUNKS = [
    {
        "content": "问题：知识库功能怎么使用？\n答案：上传知识库文件后即可使用……",
        "similarity": 0.86,
    },
    {
        "content": "问题：打印机如何连接 WIFI？\n答案：长按配网键 3 秒……",
        "similarity": 0.62,
    },
    {"content": "问题：怎么充电？", "similarity": 0.11},
]


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.encoding = None

    @property
    def text(self):
        return json.dumps(self._payload, ensure_ascii=False)

    def raise_for_status(self):
        pass


class _FakeAsyncClient:
    last_payload = None

    def __init__(self, *_args, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, url, json=None, headers=None):  # noqa: A002
        _FakeAsyncClient.last_payload = json
        return _FakeResponse({"code": 0, "data": {"chunks": CHUNKS}})


class _FakeDialogue:
    def __init__(self):
        self.dialogue = []

    def put(self, msg):
        self.dialogue.append(msg)


class _FakeTTS:
    def __init__(self):
        self.spoken = []
        self.spoken_event = threading.Event()
        self.tts_text_queue = types.SimpleNamespace(put=lambda _x: None)

    def store_tts_text(self, _sentence_id, _text):
        pass

    def tts_one_sentence(self, _conn, _content_type, content_detail=None):
        self.spoken.append(content_detail)
        self.spoken_event.set()


class _FakeIntent:
    async def replyResult(self, _text, _original_text):
        return "知识库功能这样用：上传知识库文件后就能直接提问。"


class _FakeConn:
    def __init__(self, plugins):
        self.config = {"plugins": plugins}
        self.logger = LOGGER
        self.dialogue = _FakeDialogue()
        self.tts = _FakeTTS()
        self.intent = _FakeIntent()
        self.func_handler = object()
        self.client_abort = False
        self.sentence_id = "sid"
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.loop = None
        self.stt_sent = []


def _plugin_config(**overrides):
    config = {
        "description": "某品牌说明书问答库",
        "base_url": "http://rag.local",
        "api_key": "ragflow-test",
        "dataset_ids": ["ds1"],
        "fallback_enabled": True,
        "fallback_min_similarity": 0.5,
    }
    config.update(overrides)
    return config


def _patch_ragflow_http(monkeypatch):
    import plugins_func.functions.search_from_ragflow as ragflow

    monkeypatch.setattr(
        ragflow,
        "httpx",
        types.SimpleNamespace(
            AsyncClient=_FakeAsyncClient,
            Timeout=lambda *_a, **_k: None,
            TimeoutException=httpx.TimeoutException,
            HTTPStatusError=httpx.HTTPStatusError,
            HTTPError=httpx.HTTPError,
        ),
    )


def _prepare(monkeypatch):
    """导入被测模块并把发送 STT 的动作替换成记录，避免依赖真实连接。"""
    import plugins_func.functions.search_from_ragflow as ragflow
    from core.handle import intentHandler

    _patch_ragflow_http(monkeypatch)

    async def _fake_send_stt(conn, text):
        conn.stt_sent.append(text)

    monkeypatch.setattr(intentHandler, "send_stt_message", _fake_send_stt)
    return ragflow, intentHandler


def test_retrieve_chunks_filters_by_similarity(monkeypatch):
    ragflow, _ = _prepare(monkeypatch)
    conn = _FakeConn({"search_from_ragflow": _plugin_config()})

    async def run():
        hits = await ragflow.retrieve_chunks(conn, "我要怎么使用知识库", 0.5)
        high = await ragflow.retrieve_chunks(conn, "我要怎么使用知识库", 0.8)
        return hits, high

    hits, high = asyncio.run(run())
    assert len(hits) == 2
    assert hits[0]["similarity"] >= hits[1]["similarity"]
    assert len(high) == 1
    # 请求体应带上配置里的 knowledge base id
    assert _FakeAsyncClient.last_payload["dataset_ids"] == ["ds1"]


def test_fallback_takes_over_when_hit(monkeypatch):
    _, intentHandler = _prepare(monkeypatch)
    conn = _FakeConn({"search_from_ragflow": _plugin_config()})

    async def run():
        conn.loop = asyncio.get_running_loop()
        handled = await intentHandler.fallback_knowledge_base(
            conn, "我要怎么使用知识库"
        )
        # 回复在线程池里生成，这里把等待放到线程里，避免卡住事件循环；
        # 也不用 asyncio.sleep（conftest 会把它替换成空实现）
        await conn.loop.run_in_executor(None, conn.tts.spoken_event.wait, 5)
        return handled

    handled = asyncio.run(run())
    try:
        assert handled is True
        assert conn.stt_sent == ["我要怎么使用知识库"]
        assert conn.dialogue.dialogue[0].role == "user"
        assert conn.dialogue.dialogue[1].role == "tool"
        assert "知识库功能怎么使用" in conn.dialogue.dialogue[1].content
        assert conn.tts.spoken, "兜底命中后应给出语音回复"
    finally:
        conn.executor.shutdown(wait=True)


def test_fallback_skipped_without_hit(monkeypatch):
    _, intentHandler = _prepare(monkeypatch)
    conn = _FakeConn(
        {"search_from_ragflow": _plugin_config(fallback_min_similarity=0.95)}
    )

    async def run():
        conn.loop = asyncio.get_running_loop()
        return await intentHandler.fallback_knowledge_base(conn, "今天天气怎么样")

    try:
        assert asyncio.run(run()) is False
        assert conn.dialogue.dialogue == []
    finally:
        conn.executor.shutdown(wait=True)


def test_fallback_disabled_or_not_configured(monkeypatch):
    _, intentHandler = _prepare(monkeypatch)

    async def run():
        disabled = _FakeConn(
            {"search_from_ragflow": _plugin_config(fallback_enabled=False)}
        )
        disabled.loop = asyncio.get_running_loop()
        first = await intentHandler.fallback_knowledge_base(disabled, "有问题吗")

        empty = _FakeConn({})
        empty.loop = asyncio.get_running_loop()
        second = await intentHandler.fallback_knowledge_base(empty, "你好")
        return first, second

    first, second = asyncio.run(run())
    assert first is False
    assert second is False
