"""S2S provider 基类，以及所有 S2S provider 共用的"设备侧扬声器"（下行音频 → 设备）。

provider 的生命周期（都在连接的事件循环上，open() 除外由 core/utils/s2s.attach_s2s 从执行器线程里调度）：
    open()                      建上游会话；抛异常 = 失败，连接回退到原版级联
    after_components_ready()    原版把 prompt 增强、工具处理器建好之后调用（执行器线程），把它们同步给上游
    on_pcm(pcm16k)              设备音频（已解 Opus，16 kHz 单声道，一帧 60 ms）
    on_text(text)               文字入口：唤醒词 detect、文字消息、结束语
    conn.client_is_listening    设备 listen start 到 stop 之间为 True，由上游 listen 处理器维护；on_pcm 据此决定送不送模型
    cancel(reason)              打断：设备 abort（reason=device）由 handleAbortMessage 调过来；模型侧 / 本地插话由 provider 自己发起
    close()                     连接关闭

下行走上游现成的节拍器（core/handle/sendAudioHandle.py 的 AudioRateController）：前 5 帧直接发给设备当缓冲，
之后严格 60 ms 一帧。为了知道"设备实际播到哪了"（打断时要把模型上下文截到那个位置）和给回声门控当参考，
每个音频包后面跟一个 message 回调，在包真正发出的那一刻记一笔。
"""
from __future__ import annotations

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from typing import Optional

from core.handle.sendAudioHandle import (
    PRE_BUFFER_COUNT,
    AUDIO_FRAME_DURATION,
    _do_send_audio,
    _get_or_create_rate_controller,
    send_display_message,
    send_tts_message,
)
from core.providers.s2s.audio import OpusFramer, Resampler
from core.utils.dialogue import Message

TAG = __name__


class DeviceSpeaker:
    """把模型的 PCM 变成设备的 Opus 帧并按节拍发出去；维护 tts start / stop 状态和已播位置。"""

    def __init__(self, conn, sample_rate: int, frame_ms: int = AUDIO_FRAME_DURATION, gate=None):
        self.conn = conn
        self.sample_rate = int(sample_rate)
        self.frame_ms = int(frame_ms)
        self.gate = gate
        self.framer = OpusFramer(self.sample_rate, self.frame_ms)
        # 回声门控的参考要 16 kHz：下行 PCM 另外重采样一份，按帧切给门控
        self._ref_rs = Resampler(self.sample_rate, 16000) if gate is not None else None
        self._ref_buf = bytearray()
        self._ref_frame_bytes = 16000 * self.frame_ms // 1000 * 2
        self.speaking = False      # 设备在播放（从第一帧发出到设备播完），回声门控与打断判定都看它
        self.generation = 0        # begin() 自增；end() 等播完后只在没有新回复接上时才清 speaking
        self.frames_sent = 0       # 本条回复里真正发给设备的帧数
        self.frames_queued = 0

    async def begin(self) -> None:
        """一条新回复开始：新的 sentence_id 让上游节拍器重置，清掉上一条的打断标记。"""
        self.conn.sentence_id = uuid.uuid4().hex
        self.conn.client_abort = False
        self.generation += 1
        self.frames_sent = 0
        self.frames_queued = 0
        self.framer.reset()
        self._ref_buf.clear()
        if self._ref_rs is not None:
            self._ref_rs.reset()

    async def push(self, pcm: bytes) -> None:
        if not pcm:
            return
        if self._ref_rs is not None:
            self._ref_buf.extend(self._ref_rs.process(pcm))
        await self._emit(self.framer.push(pcm))

    async def end(self) -> None:
        """回复结束（模型生成完）：尾巴补零编出来，等设备真的播完再发 tts stop、再清 speaking。
        模型生成比实时快得多，生成完时设备往往还要播好几秒；这几秒里回声门控必须仍当作"在播放"，
        否则残余回声直接进模型，模型侧 VAD 把自己的声音当成用户开口（10-31 真机：连环 turn_detected）。"""
        if self.speaking or self.frames_queued:
            await self._emit(self.framer.flush())
        if not self.speaking:
            return
        gen = self.generation
        await send_tts_message(self.conn, "stop")  # 上游实现：等队列清空 + 预缓冲播放时间，再发 stop、清 client_is_speaking
        if self.generation != gen:
            return  # 等待期间已经有新回复接上（begin 过了）：播放状态由新回复接管
        self.speaking = False
        if self.gate is not None:
            self.gate.on_tts_stop(time.monotonic())
        if self.conn.close_after_chat:
            await self.conn.close()

    async def interrupt(self) -> None:
        """被打断：丢掉还没发的帧。tts stop 消息由 handleAbortMessage 负责。"""
        self.speaking = False
        self.framer.reset()
        self._ref_buf.clear()
        rc = getattr(self.conn, "audio_rate_controller", None)
        if rc is not None:
            rc.reset()
        if self.gate is not None:
            self.gate.on_tts_stop(time.monotonic())

    def played_ms(self) -> int:
        """设备大约播到了本条回复的第几毫秒：已发出的帧减去设备侧预缓冲（前 PRE_BUFFER_COUNT 帧一次性发出）。"""
        return max(0, (self.frames_sent - PRE_BUFFER_COUNT) * self.frame_ms)

    async def _emit(self, frames: list[bytes]) -> None:
        if not frames:
            return
        conn = self.conn
        if not self.speaking:
            self.speaking = True
            if self.gate is not None:
                self.gate.on_tts_start(time.monotonic())
            await send_tts_message(conn, "start")
            conn.client_is_speaking = True
        rc, fc = _get_or_create_rate_controller(conn, self.frame_ms, True, 0)
        for opus in frames:
            if conn.client_abort:
                return
            conn.last_activity_time = time.time() * 1000
            self.frames_queued += 1
            if fc["packet_count"] < PRE_BUFFER_COUNT:
                await _do_send_audio(conn, opus, fc)
                self._mark_sent()
            else:
                rc.add_audio(opus)
                rc.add_message(self._mark_sent_async)

    def _mark_sent(self) -> None:
        self.frames_sent += 1
        if self.gate is not None:
            n = self._ref_frame_bytes
            ref = bytes(self._ref_buf[:n])
            del self._ref_buf[:n]
            if len(ref) < n:
                ref = ref + b"\x00" * (n - len(ref))
            self.gate.on_downlink(ref, time.monotonic())

    async def _mark_sent_async(self) -> None:
        self._mark_sent()


class S2SProviderBase(ABC):
    def __init__(self, config: dict, conn):
        self.config = config or {}
        self.conn = conn
        self.logger = conn.logger
        self._tasks: set[asyncio.Task] = set()
        self.speaker: Optional[DeviceSpeaker] = None

    # ---------- 生命周期 ----------
    @abstractmethod
    async def open(self) -> None:
        """建上游会话。抛异常 = 失败，attach_s2s 会让连接回退到原版级联。"""

    def after_components_ready(self) -> None:
        """原版组件（prompt 增强、工具处理器）就绪后被调用，注意在执行器线程里；要发消息请 run_coroutine_threadsafe。"""

    async def close(self) -> None:
        for t in list(self._tasks):
            t.cancel()
        if self.speaker is not None:
            await self.speaker.interrupt()

    # ---------- 设备侧事件 ----------
    @abstractmethod
    async def on_pcm(self, pcm16k: bytes) -> None:
        """设备上行 PCM（16 kHz 单声道，60 ms 一帧）。"""

    @abstractmethod
    async def on_text(self, text: str) -> None:
        """文字入口（唤醒词 detect、文字消息）。"""

    def on_listen(self, state: str | None, mode: str | None) -> None:
        """保留给需要额外处理 listen 消息的 provider；聆听开关本身看 conn.client_is_listening（上游 listen 处理器维护）。"""

    @abstractmethod
    async def cancel(self, reason: str) -> None:
        """打断。reason：device（设备按键，经 handleAbortMessage）、server（模型侧判出有人开口）、local（本地门控）。"""

    # ---------- 公用小工具 ----------
    def spawn(self, coro) -> asyncio.Task:
        t = asyncio.ensure_future(coro)
        self._tasks.add(t)
        t.add_done_callback(self._tasks.discard)
        return t

    async def show_user_text(self, text: str) -> None:
        """用户说了什么：设备屏幕显示 + 写进对话历史（记忆用）。"""
        if not text:
            return
        self.conn.dialogue.put(Message(role="user", content=text))
        try:
            await send_display_message(self.conn, text)
        except Exception:  # noqa: BLE001
            pass

    async def show_assistant_text(self, text: str) -> None:
        if not text:
            return
        self.conn.dialogue.put(Message(role="assistant", content=text))
        try:
            await send_tts_message(self.conn, "sentence_start", text)
        except Exception:  # noqa: BLE001
            pass
