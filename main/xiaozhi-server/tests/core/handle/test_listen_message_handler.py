
import asyncio
from types import SimpleNamespace

import pytest


@pytest.fixture
def handler_module(monkeypatch):
    # 复用项目 conftest.py 提供的测试配置
    from config import settings

    monkeypatch.setattr(settings, "config_file_valid", True)

    # 必须在配置检查之后导入业务模块
    from core.handle.textHandler import listenMessageHandler

    return listenMessageHandler


def create_connection():
    return SimpleNamespace(
        client_have_voice=False,
        last_activity_time=0,
        just_woken_up=False,
        reset_audio_states=lambda: None,
        config={
            "wakeup_words": ["你好小智"],
            "enable_greeting": True,
        },
    )


def test_wakeup_word_passes_filtered_text(handler_module, monkeypatch):
    """唤醒词清理后传给聊天和 ASR 上报。"""

    calls = {}

    async def fake_start_to_chat(conn, text):
        calls["chat"] = text

    def fake_enqueue_asr_report(conn, text, opus_data):
        calls["report"] = text

    monkeypatch.setattr(
        handler_module, "startToChat", fake_start_to_chat
    )
    monkeypatch.setattr(
        handler_module, "enqueue_asr_report", fake_enqueue_asr_report
    )

    conn = create_connection()
    handler = handler_module.ListenTextMessageHandler()

    original_text = "你好，小智！"

    asyncio.run(
        handler.handle(conn, {
            "state": "detect",
            "text": original_text
        })
    )

    assert calls["chat"] == "你好小智"
    assert calls["report"] == "你好小智"


def test_normal_text_keeps_original_text(handler_module, monkeypatch):
    """普通文本保留原文和标点。"""

    calls = {}

    async def fake_start_to_chat(conn, text):
        calls["chat"] = text

    def fake_enqueue_asr_report(conn, text, opus_data):
        calls["report"] = text

    monkeypatch.setattr(
        handler_module, "startToChat", fake_start_to_chat
    )
    monkeypatch.setattr(
        handler_module, "enqueue_asr_report", fake_enqueue_asr_report
    )

    conn = create_connection()
    handler = handler_module.ListenTextMessageHandler()

    original_text = "你好，小智，我有问题。"

    asyncio.run(
        handler.handle(conn, {
            "state": "detect",
            "text": original_text
        })
    )

    assert calls["chat"] == original_text
    assert calls["report"] == original_text
