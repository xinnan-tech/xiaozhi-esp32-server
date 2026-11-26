import asyncio
import queue
from types import SimpleNamespace

from core.providers.asr import base as asr_base
from core.providers.asr.base import ASRProviderBase


class DummyASR(ASRProviderBase):
    async def speech_to_text(self, opus_data, session_id, artifacts=None):
        return "", None


def _make_conn(have_voice):
    tts_queue = queue.Queue()
    return SimpleNamespace(
        client_have_voice=have_voice,
        tts=SimpleNamespace(tts_text_queue=tts_queue),
        session_id="s-1",
    )


def test_silence_only_logs(monkeypatch):
    sent = []

    async def fake_send_stt(conn, text):
        sent.append(text)

    monkeypatch.setattr(asr_base, "send_stt_message", fake_send_stt)
    conn = _make_conn(have_voice=False)
    asyncio.run(DummyASR().notify_empty_asr(conn, had_voice=False))
    assert sent == []
    assert conn.tts.tts_text_queue.empty()


def test_voice_with_empty_asr_prompts_user(monkeypatch):
    sent = []

    async def fake_send_stt(conn, text):
        sent.append(text)

    monkeypatch.setattr(asr_base, "send_stt_message", fake_send_stt)
    conn = _make_conn(have_voice=True)
    asyncio.run(DummyASR().notify_empty_asr(conn, had_voice=True))

    assert sent == [asr_base.EMPTY_ASR_PROMPT]
    kinds = []
    while not conn.tts.tts_text_queue.empty():
        kinds.append(conn.tts.tts_text_queue.get_nowait())
    # FIRST / MIDDLE / LAST 三个消息，且同一 sentence_id
    assert [m.sentence_type.name for m in kinds] == ["FIRST", "MIDDLE", "LAST"]
    assert len({m.sentence_id for m in kinds}) == 1
    assert kinds[1].content_detail == asr_base.EMPTY_ASR_PROMPT


def test_prompt_failure_does_not_raise(monkeypatch):
    async def boom(conn, text):
        raise RuntimeError("ws gone")

    monkeypatch.setattr(asr_base, "send_stt_message", boom)
    conn = _make_conn(have_voice=True)
    # 不应向上抛异常影响连接
    asyncio.run(DummyASR().notify_empty_asr(conn, had_voice=True))
