"""S2S 音频工具：重采样（audioop 与 numpy 两条路径）、Opus 分帧。"""
from __future__ import annotations

import numpy as np
import pytest

from core.providers.s2s import audio as audio_mod
from core.providers.s2s.audio import OpusFramer, Resampler


def _tone(rate: int, ms: int, hz: float = 440.0, amp: int = 8000) -> bytes:
    n = rate * ms // 1000
    t = np.arange(n) / rate
    return (np.sin(2 * np.pi * hz * t) * amp).astype(np.int16).tobytes()


@pytest.mark.parametrize("use_audioop", [True, False])
def test_resample_16k_to_24k_keeps_duration_and_tone(monkeypatch, use_audioop):
    if use_audioop and audio_mod.audioop is None:
        pytest.skip("本解释器没有 audioop")
    if not use_audioop:
        monkeypatch.setattr(audio_mod, "audioop", None)
    rs = Resampler(16000, 24000)
    out = b"".join(rs.process(_tone(16000, 60)) for _ in range(10))  # 10 帧 × 60 ms，分帧送进去
    n_in, n_out = 16000 * 600 // 1000, len(out) // 2
    assert abs(n_out - n_in * 3 // 2) <= 4  # 时长按 3:2 放大，允许边界差几样本
    y = np.frombuffer(out, np.int16).astype(np.float64)
    spec = np.abs(np.fft.rfft(y[2400:]))        # 去掉开头的过渡
    peak_hz = np.fft.rfftfreq(len(y[2400:]), 1 / 24000)[int(np.argmax(spec))]
    assert abs(peak_hz - 440) < 10


def test_resample_same_rate_is_identity_and_empty_is_empty():
    rs = Resampler(24000, 24000)
    pcm = _tone(24000, 20)
    assert rs.process(pcm) == pcm and rs.process(b"") == b""


def test_opus_framer_cuts_60ms_frames_and_flushes_tail():
    try:
        fr = OpusFramer(24000, 60)
    except Exception as e:  # noqa: BLE001  （conftest 可能把 opuslib_next 桩掉）
        pytest.skip(f"Opus 编码器不可用: {type(e).__name__}")
    pcm = _tone(24000, 150)                     # 2.5 帧
    frames = fr.push(pcm)
    assert len(frames) == 2 and all(isinstance(f, bytes) and len(f) > 0 for f in frames)
    tail = fr.flush()
    assert len(tail) == 1                       # 剩下半帧补零编出来
    assert fr.flush() == []                     # 再 flush 没有东西
    fr.reset()
    assert fr.push(_tone(24000, 60)) and len(fr.push(b"")) == 0
