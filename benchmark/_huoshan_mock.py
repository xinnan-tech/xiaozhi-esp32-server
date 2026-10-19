"""huoshan_double_stream 4 bug 复现脚本的共享 mock 工具。"""
from __future__ import annotations

import asyncio
import os
import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(REPO, "main", "xiaozhi-server")
if SERVER not in sys.path:
    sys.path.insert(0, SERVER)


class FakeConn:
    sample_rate = 24000
    stop_event = asyncio.Event()
    loop = None
    sentence_id = "test-session-id"
    client_abort = False

    def __init__(self):
        self.stop_event = asyncio.Event()


def build_provider() -> Any:
    """绕开 TTSProvider.__init__ 复杂依赖，构造一个可直接调方法的实例。"""
    from core.providers.tts import huoshan_double_stream as mod

    p = mod.TTSProvider.__new__(mod.TTSProvider)
    p.ws = MagicMock()
    p.ws.send = AsyncMock()
    p.ws.recv = AsyncMock()
    p.ws.close = AsyncMock()
    p.conn = FakeConn()
    p.voice = "test-voice"
    p.activate_session = False
    p._monitor_task = None
    p._pending_prefix = ""
    p.tts_text = ""
    p.tts_audio_queue = MagicMock()
    p.before_stop_play_files = []
    p.tts_timeout = 1.0
    p.enable_ws_reuse = False
    p.resource_type = False
    p.tts_text_buff = []
    p.processed_chars = 0
    p._correct_words_pattern = None
    p.audio_params = {"speech_rate": 0, "loudness_rate": 0}
    p.additions = {"aigc_metadata": {}, "cache_config": {}, "post_process": {"pitch": 0}}
    p.mix_speaker = {}
    p.opus_encoder = MagicMock()
    p.opus_encoder.reset_state = MagicMock()
    p.opus_encoder.encode_pcm_to_opus_stream = MagicMock(return_value=b"")
    p.handle_opus = MagicMock()
    p._process_before_stop_play_files = MagicMock()
    p.text_to_speak = AsyncMock()
    p._ensure_connection = AsyncMock()
    p.send_event = AsyncMock()
    p.send_text = AsyncMock()
    p.finish_connection = AsyncMock()
    p.close = AsyncMock()
    p.print_response = MagicMock()
    return p


def run(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
