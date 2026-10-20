"""Wakeup caching accepts both return forms of TTSProviderBase.to_tts."""

import asyncio
import math
import struct
import wave
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def wakeup_runtime(tmp_path, monkeypatch):
    # conftest supplies local configuration; no deployment config is required.
    from config import settings

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(settings, "config_file_valid", True)
    from core.handle import helloHandle
    from core.providers.tts.base import TTSProviderBase
    from core.utils.wakeup_word import WakeupWordsConfig

    class LocalTTS(TTSProviderBase):
        """Replace only remote synthesis; keep the real file and Opus conversion."""

        def __init__(self, output_dir, delete_audio_file):
            super().__init__({"output_dir": str(output_dir)}, delete_audio_file)
            self.voice = "test-voice"
            self.filename = output_dir / "retained.wav"
            buffer = BytesIO()
            with wave.open(buffer, "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(22050)
                audio.writeframes(
                    b"".join(
                        struct.pack(
                            "<h", int(8000 * math.sin(2 * math.pi * 440 * i / 22050))
                        )
                        # 1.1s 源音频：给重采样留裕量，规避重采样器 off-by-one
                        for i in range(int(22050 * 1.1))
                    )
                )
            self.audio_bytes = buffer.getvalue()

        def generate_filename(self):
            return str(self.filename)

        async def text_to_speak(self, text, output_file):
            if output_file is not None:
                Path(output_file).write_bytes(self.audio_bytes)
            return self.audio_bytes

    cache = WakeupWordsConfig()
    monkeypatch.setattr(helloHandle, "wakeup_words_config", cache)
    monkeypatch.setattr(helloHandle, "_wakeup_response_lock", asyncio.Lock())
    return helloHandle, cache, LocalTTS


@pytest.mark.parametrize("sample_rate", [16000, 24000])
@pytest.mark.parametrize("delete_audio_file", [False, True])
def test_wakeup_cache_accepts_retained_files_and_opus_frames(
    tmp_path, wakeup_runtime, sample_rate, delete_audio_file
):
    helloHandle, wakeup_cache, LocalTTS = wakeup_runtime
    tts = LocalTTS(tmp_path, delete_audio_file)
    conn = SimpleNamespace(tts=tts, sample_rate=sample_rate)
    tts.conn = conn

    asyncio.run(helloHandle.wakeupWordsResponse(conn))

    response = wakeup_cache.get_wakeup_response(tts.voice)
    assert response is not None
    assert response["text"] in helloHandle.WAKEUP_CONFIG["responses"]
    with wave.open(response["file_path"], "rb") as audio:
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getframerate() == sample_rate
        assert audio.getnframes() >= sample_rate
        assert any(audio.readframes(audio.getnframes()))
    if not delete_audio_file:
        assert tts.filename.read_bytes() == tts.audio_bytes
    assert not helloHandle._wakeup_response_lock.locked()


@pytest.mark.parametrize("tts_result", [None, []])
def test_empty_synthesis_does_not_replace_cached_response(wakeup_runtime, tts_result):
    helloHandle, wakeup_cache, _ = wakeup_runtime
    wakeup_cache.generate_file_path = Mock()
    wakeup_cache.update_wakeup_response = Mock()
    conn = SimpleNamespace(tts=SimpleNamespace(to_tts=lambda _: tts_result))

    asyncio.run(helloHandle.wakeupWordsResponse(conn))

    wakeup_cache.generate_file_path.assert_not_called()
    wakeup_cache.update_wakeup_response.assert_not_called()
    assert not helloHandle._wakeup_response_lock.locked()


def test_retained_file_skips_opus_roundtrip(wakeup_runtime, tmp_path, monkeypatch):
    """保留文件路径必须直转 wav，不得经过 Opus 编解码。"""
    from core.utils import util

    helloHandle, wakeup_cache, LocalTTS = wakeup_runtime

    def _forbid_opus(*_args, **_kwargs):
        raise AssertionError("retained file path must not run Opus encoding")

    monkeypatch.setattr(util, "pcm_to_data_stream", _forbid_opus)
    tts = LocalTTS(tmp_path, False)
    conn = SimpleNamespace(tts=tts, sample_rate=16000)
    tts.conn = conn

    asyncio.run(helloHandle.wakeupWordsResponse(conn))

    assert wakeup_cache.get_wakeup_response(tts.voice) is not None


def test_missing_retained_file_preserves_cache_and_releases_lock(wakeup_runtime):
    helloHandle, wakeup_cache, _ = wakeup_runtime
    wakeup_cache.generate_file_path = Mock()
    wakeup_cache.update_wakeup_response = Mock()
    conn = SimpleNamespace(
        tts=SimpleNamespace(voice="test-voice", to_tts=lambda _: "missing.wav"),
        sample_rate=16000,
    )

    with pytest.raises(FileNotFoundError):
        asyncio.run(helloHandle.wakeupWordsResponse(conn))

    wakeup_cache.generate_file_path.assert_not_called()
    wakeup_cache.update_wakeup_response.assert_not_called()
    assert not helloHandle._wakeup_response_lock.locked()
