"""一级残余回声门控：S2S provider 在把设备上行送给模型之前，用它压掉设备端 AEC 剩下的回声。

为什么需要（2026-10-20 ESP32-S3 真机实测）：设备端 AEC 之后，播放期间上行仍有与播放内容相关的残余：安静时 RMS 中位 25，
播放时峰值可到 1200，包络与下行相关、滞后稳定；模型侧 VAD 会把它当成用户开口，模型播到 0.5 秒就被自己打断、
再接着回答自己的回声。门控打开后同样的场景 0 次误触发。

做法：provider 知道自己发了什么、什么时候发的：
  1. 参考 = 本段第一帧发送时刻起、按设备实际播放排列的下行 PCM（断流处补零）；
  2. 滞后先验 200 ms，0～1200 ms 内按 50 ms 对数包络互相关复估（插话多时跳过）；
  3. 回声回传比 g = 播放期间"上行功率 / 参考尾窗最大功率"的 90% 分位；
  4. 每 20 ms 子帧判：上行功率 > α·g·P_ref + (2×底噪)²，且 silero 判为人声 → 整帧放行并保持 300 ms；
     否则整帧换成底噪水平的舒适噪声。设备不在播放、或这一帧对应的时间窗里设备没放东西时直通。
silero 直接用上游自带的 onnx 模型（models/snakers4_silero-vad），不装 torch；模型文件不在时只用能量判据并记一条警告。
"""
from __future__ import annotations

import collections
import math
import os
from pathlib import Path

import numpy as np

from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

RATE = 16000
SUB = RATE * 20 // 1000  # 20 ms 子帧 = 320 样本
ENV_S = 0.02
DEFAULT_VAD_MODEL = Path("models/snakers4_silero-vad/src/silero_vad/data/silero_vad.onnx")

_SESSIONS: dict[str, object] = {}  # 模型只加载一次，各会话各自保存状态


class SileroVAD:
    """silero VAD 的 onnx 推理（16 kHz、每次 512 样本 + 64 样本上下文），与上游 core/providers/vad/silero.py 同一模型。"""

    def __init__(self, path: Path):
        key = str(path)
        if key not in _SESSIONS:
            import onnxruntime as ort

            opts = ort.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1
            _SESSIONS[key] = ort.InferenceSession(key, sess_options=opts, providers=["CPUExecutionProvider"])
        self.sess = _SESSIONS[key]
        self.reset_states()

    def reset_states(self) -> None:
        self.state = np.zeros((2, 1, 128), dtype=np.float32)
        self.context = np.zeros((1, 64), dtype=np.float32)

    def __call__(self, chunk: np.ndarray) -> float:
        """chunk：512 个 float32 样本（−1～1）。返回人声概率。"""
        x = np.concatenate([self.context, chunk.reshape(1, -1).astype(np.float32)], axis=1)
        out, self.state = self.sess.run(None, {"input": x, "state": self.state, "sr": np.array(16000, dtype=np.int64)})
        self.context = x[:, -64:]
        return float(np.asarray(out).reshape(-1)[0])


def load_vad(path: str | os.PathLike | None = None):
    p = Path(path or DEFAULT_VAD_MODEL)
    if not p.exists():
        logger.bind(tag=TAG).warning(f"silero VAD 模型不存在（{p}），回声门控只用能量判据")
        return None
    return SileroVAD(p)


class EchoGate:
    def __init__(self, alpha=2.0, floor_rms=25.0, g_quantile=0.90, g_prior=1e-2, lag_prior=0.20,
                 lag_min=0.0, lag_max=1.20, lag_step=0.02, lag_every=5.0, hold_s=0.30,
                 tail_back=0.12, tail_fwd=0.04, vad_threshold=0.5, vad=None, log_fn=None, seed=0,
                 start_window: tuple[float, float] | None = (0.08, 0.65)):
        """默认值来自真机：公网入口下滞后 160～520 ms（相对本段第一帧发送时刻），残余回声相对参考 −8～−50 dB 起伏，
        上行到达抖动中位 31 ms、最大 143 ms（所以音频时钟按帧序号重建）。vad=None 表示只用能量判据。
        start_window=(最短, 最长) 秒：还没估出滞后之前，参考窗放宽到覆盖这段回声延迟（会话开头先验常常不准，
        窄窗盖不住，唤醒应答的回声漏给模型，模型去回答自己的回声）。"""
        self.alpha = alpha
        self.floor_rms = floor_rms
        self.g_quantile = g_quantile
        self.g_prior = g_prior
        self.lag = lag_prior
        self.lag_corr = None
        self.lag_min, self.lag_max, self.lag_step, self.lag_every = lag_min, lag_max, lag_step, lag_every
        self.hold_s = hold_s
        self.tail_back, self.tail_fwd = tail_back, tail_fwd
        self.start_window = start_window
        self.vad_threshold = vad_threshold
        self.vad = vad
        self.t_audio = None
        self.log = log_fn or (lambda m: logger.bind(tag=TAG).info(m))
        self.rng = np.random.default_rng(seed)
        self.seg_t0 = None
        self.seg_buf = bytearray()
        self.seg_end = None
        self.ratios = collections.deque(maxlen=250)
        self.up_env = collections.deque(maxlen=400)
        self.t_last_lag = -1e9
        self.g = None
        self.hold_until = -1.0
        self.recent = collections.deque(maxlen=100)
        self.stats = {"frames": 0, "bypass": 0, "pass": 0, "echo": 0, "lag_est": 0, "noref": 0, "lag_skip_barge": 0}

    # ---------- 事件 ----------
    @property
    def seg(self) -> np.ndarray:
        return np.frombuffer(self.seg_buf, dtype=np.int16)  # 视图，不拷贝；别长期持有

    def on_tts_start(self, t: float) -> None:
        self.seg_t0 = None
        self.seg_buf = bytearray()
        self.seg_end = None
        self.up_env.clear()
        if self.vad is not None:
            self.vad.reset_states()

    def on_downlink(self, pcm_bytes: bytes, t_send: float) -> None:
        """设备收到一帧就排进播放队列：本帧开播时刻 = max(发送时刻, 上一帧播完)。断流时中间补零。pcm 是 16 kHz。"""
        if self.seg_t0 is None:
            self.seg_t0 = t_send
        end_t = self.seg_t0 + len(self.seg_buf) / 2 / RATE
        gap = t_send - end_t
        if gap > 0.03:
            self.seg_buf.extend(b"\x00\x00" * int(gap * RATE))
        self.seg_buf.extend(pcm_bytes)

    def on_tts_stop(self, t: float) -> None:
        self.seg_end = t

    # ---------- 内部 ----------
    def _window(self) -> tuple[float, float]:
        if self.lag_corr is None and self.start_window:
            lo, hi = self.start_window
            return max(self.tail_back, hi - self.lag), max(self.tail_fwd, self.lag - lo)
        return self.tail_back, self.tail_fwd

    def _active(self, t: float, speaking: bool) -> bool:
        if speaking and self.seg_t0 is not None:
            return True
        return self.seg_end is not None and self.seg_t0 is not None and t - self.seg_end < self.lag + self._window()[0] + 0.18

    def _ref_sub(self, t_sub: float):
        if self.seg_t0 is None:
            return None
        idx = int(round((t_sub - self.lag - self.seg_t0) * RATE))
        if idx < 0 or idx + SUB > len(self.seg_buf) // 2:
            return None
        return np.frombuffer(self.seg_buf, dtype=np.int16, count=SUB, offset=idx * 2)

    def _ref_power(self, t_sub: float):
        best = None
        tail_back, tail_fwd = self._window()
        off = -tail_back
        while off <= tail_fwd + 1e-9:
            r = self._ref_sub(t_sub + off)
            if r is not None:
                p = float(np.mean(r.astype(np.float64) ** 2))
                best = p if best is None else max(best, p)
            off += ENV_S
        return best

    def _estimate_lag(self, t: float) -> None:
        if len(self.up_env) < 100 or len(self.seg_buf) < 2 * RATE:
            self.t_last_lag = t - self.lag_every + 0.5
            return
        if self.recent and sum(self.recent) / len(self.recent) > 0.3:
            self.stats["lag_skip_barge"] += 1
            self.t_last_lag = t - self.lag_every + 1.0
            return
        self.t_last_lag = t
        ups = np.array(self.up_env, dtype=np.float64)
        W = 0.05
        seg = self.seg.astype(np.float64)
        n_env = int(len(seg) / RATE / W)
        wlen = int(RATE * W)
        ref_env = np.sqrt(np.mean(seg[:n_env * wlen].reshape(n_env, wlen) ** 2, axis=1))
        del seg
        quiet = ups[:, 1] <= np.median(ups[:, 1])
        up_log = np.log10(ups[:, 1] + 1.0)
        ref_log = np.log10(ref_env + 1.0)
        best_c, best_lag = -1.0, None
        for lag in np.arange(self.lag_min, self.lag_max + 1e-9, self.lag_step):
            k = np.floor((ups[:, 0] - lag - self.seg_t0) / W + 1e-6).astype(int)
            m = (k >= 0) & (k < n_env) & quiet
            if m.sum() < 30:
                continue
            x, y = up_log[m], ref_log[k[m]]
            if x.std() < 1e-6 or y.std() < 1e-6:
                continue
            c = float(np.corrcoef(x, y)[0, 1])
            if c > best_c:
                best_c, best_lag = c, float(lag)
        self.stats["lag_est"] += 1
        accept = best_lag is not None and (best_c >= 0.5 or (best_c >= 0.25 and abs(best_lag - self.lag) <= 0.10))
        if accept:
            old = self.lag
            self.lag, self.lag_corr = best_lag, best_c
            self.log(f"echo gate lag {old * 1000:.0f} -> {best_lag * 1000:.0f} ms (corr {best_c:.2f})")
        else:
            self.t_last_lag = t - self.lag_every + 1.0

    def _vad_prob(self, a: np.ndarray) -> float:
        if self.vad is None:
            return 1.0
        x = a.astype(np.float32) / 32768.0
        probs = []
        for start in (0, max(0, len(x) - 512)):
            chunk = x[start:start + 512]
            if len(chunk) < 512:
                chunk = np.pad(chunk, (0, 512 - len(chunk)))
            probs.append(self.vad(chunk))
        return max(probs)

    # ---------- 主入口 ----------
    def process(self, pcm_bytes: bytes, t_recv: float, speaking: bool) -> tuple[bytes, str]:
        """返回 (送给模型的 PCM, 判决)。判决首词：bypass / noref / pass / echo。t_recv 是这 60 ms 帧到达的时刻。"""
        self.stats["frames"] += 1
        a = np.frombuffer(pcm_bytes, dtype=np.int16)
        if self.t_audio is None:
            self.t_audio = t_recv
        else:
            self.t_audio += 0.06
            if t_recv - self.t_audio > 0.2 or self.t_audio - t_recv > 0.1:
                self.t_audio = t_recv
        t_frame = self.t_audio
        if not self._active(t_frame, speaking):
            self.stats["bypass"] += 1
            return pcm_bytes, "bypass"
        floor_p = (2.0 * self.floor_rms) ** 2
        g = self.g if self.g is not None else self.g_prior
        any_pass = False
        n_ref = 0
        for i in range(len(a) // SUB):
            sub = a[i * SUB:(i + 1) * SUB].astype(np.float64)
            t_sub = t_frame - 0.06 + i * ENV_S + 0.01
            p_up = float(np.mean(sub ** 2))
            self.up_env.append((t_sub, math.sqrt(p_up)))
            p_ref = self._ref_power(t_sub)
            if p_ref is None:
                continue
            n_ref += 1
            if p_ref > 1e3:
                self.ratios.append(p_up / p_ref)
            if p_up > self.alpha * g * p_ref + floor_p:
                any_pass = True
        if n_ref == 0:
            self.stats["noref"] += 1
            self.recent.append(0)
            return pcm_bytes, "noref"
        if len(self.ratios) >= 50:
            self.g = float(np.quantile(np.array(self.ratios), self.g_quantile))
        if (self.lag_corr is None and t_frame - self.t_last_lag >= 2.4) or t_frame - self.t_last_lag >= self.lag_every:
            self._estimate_lag(t_frame)
        vad_p = self._vad_prob(a) if any_pass or t_frame < self.hold_until else 0.0
        fresh = any_pass and vad_p >= self.vad_threshold
        if fresh:
            self.hold_until = t_frame + self.hold_s
        if fresh or t_frame < self.hold_until:
            self.stats["pass"] += 1
            self.recent.append(1)
            return pcm_bytes, "pass"
        self.stats["echo"] += 1
        self.recent.append(0)
        noise = self.rng.normal(0.0, self.floor_rms, len(a)).astype(np.int16)
        return noise.tobytes(), "echo"
