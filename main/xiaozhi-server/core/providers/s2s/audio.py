"""S2S 共用的音频工具：重采样、PCM → 60 ms Opus 帧。

设备侧：上行是 16 kHz 单声道 PCM（上游在 connection.py 里已经把 Opus 解开）；下行按 hello 里的 audio_params 编 Opus
（默认 24 kHz，见 config.yaml 的 xiaozhi.audio_params）。
模型侧：OpenAI Realtime 的 audio/pcm 只收发 24 kHz。所以上行要 16 k → 24 k，下行多数情况不用再采样。

重采样优先用标准库 audioop.ratecv（Python 3.10 / 3.11 有，3.13 移除）；没有时退到 numpy 线性插值，音质够语音用。
"""
from __future__ import annotations

import warnings

import numpy as np

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import audioop  # type: ignore
except ImportError:  # Python >= 3.13
    audioop = None

from core.utils.opus_encoder_utils import OpusEncoderUtils


class Resampler:
    """16 位单声道 PCM 流式重采样，保留跨包状态，连续调用不产生接缝。"""

    def __init__(self, src_rate: int, dst_rate: int):
        self.src_rate = int(src_rate)
        self.dst_rate = int(dst_rate)
        self.reset()

    def reset(self) -> None:
        self._state = None
        self._last = 0.0  # numpy 路径：上一包最后一个样本
        self._pos = 0.0   # numpy 路径：下一个输出样本在输入轴上的小数位置

    def process(self, pcm: bytes) -> bytes:
        if not pcm:
            return b""
        if self.src_rate == self.dst_rate:
            return bytes(pcm)
        if audioop is not None:
            out, self._state = audioop.ratecv(pcm, 2, 1, self.src_rate, self.dst_rate, self._state)
            return out
        return self._numpy_resample(pcm)

    def _numpy_resample(self, pcm: bytes) -> bytes:
        x = np.frombuffer(pcm, dtype=np.int16).astype(np.float64)
        # 把上一包的最后一个样本接在前面，位置轴：-1 是它，0..n-1 是本包
        src = np.concatenate(([self._last], x))
        ratio = self.src_rate / self.dst_rate
        n = len(x)
        positions = []
        p = self._pos
        while p < n:
            positions.append(p)
            p += ratio
        self._pos = p - n
        self._last = float(x[-1])
        if not positions:
            return b""
        pos = np.asarray(positions)
        idx = np.floor(pos).astype(int)          # -1 .. n-1  → src 下标 idx+1
        frac = pos - idx
        a = src[idx + 1]
        b = src[np.minimum(idx + 2, n)]
        y = a + (b - a) * frac
        return np.clip(np.rint(y), -32768, 32767).astype(np.int16).tobytes()


class OpusFramer:
    """把任意长度的 PCM 攒成固定时长的 Opus 帧（默认 60 ms），用上游的 OpusEncoderUtils。"""

    def __init__(self, sample_rate: int, frame_ms: int = 60):
        self.sample_rate = int(sample_rate)
        self.frame_ms = int(frame_ms)
        self.frame_bytes = self.sample_rate * self.frame_ms // 1000 * 2
        self._enc = OpusEncoderUtils(self.sample_rate, 1, self.frame_ms)

    def push(self, pcm: bytes) -> list[bytes]:
        frames: list[bytes] = []
        if pcm:
            self._enc.encode_pcm_to_opus_stream(pcm, False, frames.append)
        return frames

    def flush(self) -> list[bytes]:
        """把不足一帧的尾巴补零编出来（回复结束时调用）。"""
        frames: list[bytes] = []
        self._enc.encode_pcm_to_opus_stream(b"", True, frames.append)
        return frames

    def reset(self) -> None:
        self._enc.reset_state()

    def close(self) -> None:
        self._enc.close()
