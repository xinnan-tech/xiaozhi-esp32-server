"""S2S 插槽的四处钩子（connection._route_message / _initialize_components、abortHandle、startToChat、listen）：
选中 S2S 时音频直接交给 provider、不建 TTS / ASR；没选中或打开失败时和原版完全一样。provider 用假的，不出网。"""
from __future__ import annotations

import asyncio
import copy
import json

import pytest

from tests.conftest import CONFIG
from config.logger import setup_logging
from core.utils.cache.manager import CacheType, cache_manager

# setup_logging() 没有配置缓存时会 asyncio.run(load_config())，在事件循环里会炸；生产由 app.py 填缓存，测试自己填
cache_manager.set(CacheType.CONFIG, "main_config", CONFIG)
setup_logging()

from core.connection import ConnectionHandler  # noqa: E402
from core.handle.abortHandle import handleAbortMessage
from core.handle.receiveAudioHandle import startToChat
from core.handle.textHandler.listenMessageHandler import ListenTextMessageHandler
import core.connection as connection_mod


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send(self, m):
        self.sent.append(m)


class FakeProvider:
    def __init__(self):
        self.pcm, self.texts, self.cancels, self.listens, self.ready = [], [], [], [], 0

    async def on_pcm(self, pcm):
        self.pcm.append(pcm)

    async def on_text(self, text):
        self.texts.append(text)

    async def cancel(self, reason):
        self.cancels.append(reason)

    def on_listen(self, state, mode):
        self.listens.append((state, mode))

    def after_components_ready(self):
        self.ready += 1

    async def close(self):
        self.closed = getattr(self, "closed", 0) + 1


def _opus_silence_frame():
    try:
        from core.utils.opus_encoder_utils import OpusEncoderUtils
        frames = []
        OpusEncoderUtils(16000, 1, 60).encode_pcm_to_opus_stream(bytes(1920), False, frames.append)
        return frames[0]
    except Exception:  # noqa: BLE001
        return None


def make_conn(loop):
    conn = ConnectionHandler(copy.deepcopy(CONFIG), None, None, None, None, None)
    conn.loop = loop
    conn.websocket = FakeWS()
    conn.need_bind = False
    conn.bind_completed_event.set()
    conn.session_id = "s"
    return conn


def test_route_message_bytes_goes_to_provider_only_when_attached():
    frame = _opus_silence_frame()
    if frame is None:
        pytest.skip("Opus 编码器不可用")

    async def go():
        conn = make_conn(asyncio.get_running_loop())
        await conn._route_message(frame)              # 没选 S2S、也没有 ASR：静默丢弃，不报错
        fake = FakeProvider()
        conn.s2s = fake
        await conn._route_message(frame)
        assert len(fake.pcm) == 1 and len(fake.pcm[0]) == 1920   # 60 ms 16 kHz PCM
        assert conn.asr_audio_queue.empty()                       # 不进 ASR 队列
    asyncio.run(go())


def test_initialize_components_skips_tts_asr_when_s2s_attached(monkeypatch):
    async def go():
        conn = make_conn(asyncio.get_running_loop())
        fake = FakeProvider()
        monkeypatch.setattr(connection_mod, "attach_s2s", lambda c: fake)
        monkeypatch.setattr(conn, "_initialize_tts", lambda: (_ for _ in ()).throw(AssertionError("不该建 TTS")))
        monkeypatch.setattr(conn, "_initialize_asr", lambda: (_ for _ in ()).throw(AssertionError("不该建 ASR")))
        monkeypatch.setattr(conn, "_init_prompt_enhancement", lambda: None)   # 不查 IP 归属地 / 天气
        monkeypatch.setattr(conn, "_inject_tool_call_fewshot", lambda: None)
        await asyncio.get_running_loop().run_in_executor(None, conn._initialize_components)
        assert conn.s2s is fake and conn.tts is None and conn.asr is None
        assert fake.ready == 1
    asyncio.run(go())


def test_initialize_components_falls_back_to_cascade_when_attach_returns_none(monkeypatch):
    class Dummy:
        def __init__(self):
            self.opened = 0

        async def open_audio_channels(self, conn):
            self.opened += 1

    async def go():
        conn = make_conn(asyncio.get_running_loop())
        tts, asr = Dummy(), Dummy()
        monkeypatch.setattr(connection_mod, "attach_s2s", lambda c: None)
        monkeypatch.setattr(conn, "_initialize_tts", lambda: tts)
        monkeypatch.setattr(conn, "_initialize_asr", lambda: asr)
        monkeypatch.setattr(conn, "_init_prompt_enhancement", lambda: None)
        monkeypatch.setattr(conn, "_inject_tool_call_fewshot", lambda: None)
        await asyncio.get_running_loop().run_in_executor(None, conn._initialize_components)
        await asyncio.sleep(0)
        assert conn.s2s is None and conn.tts is tts and conn.asr is asr
        assert tts.opened == 1 and asr.opened == 1
    asyncio.run(go())


def test_text_abort_and_listen_hooks_reach_provider():
    async def go():
        conn = make_conn(asyncio.get_running_loop())
        fake = FakeProvider()
        conn.s2s = fake
        await startToChat(conn, "现在几点")
        assert fake.texts == ["现在几点"]
        conn.client_is_speaking = True
        await handleAbortMessage(conn)
        assert fake.cancels == ["device"] and conn.client_abort is True and conn.client_is_speaking is False
        assert json.loads(conn.websocket.sent[-1]) == {"type": "tts", "state": "stop", "session_id": "s"}
        assert conn.client_is_listening is False
        await ListenTextMessageHandler().handle(conn, {"state": "start", "mode": "realtime"})
        assert conn.client_is_listening is True and conn.client_listen_mode == "realtime"
        await ListenTextMessageHandler().handle(conn, {"state": "detect", "text": "你好小智"})
        assert conn.client_is_listening is True and fake.texts[-1] == "嘿，你好呀"  # detect 不改聆听状态；唤醒词被上游换成固定问候句再进 startToChat
        await ListenTextMessageHandler().handle(conn, {"state": "stop"})
        assert conn.client_is_listening is False
        await conn.close()                                   # 设备断开 → 上游会话跟着关
        assert fake.closed == 1
    asyncio.run(go())
