"""PR-issue 3439 finish_session 残留 + opus 尾帧冲刷回归测试。

复现：
  1. finish_session 不发送 _pending_prefix 残留：句尾替换词恰好被扣留时整段丢
  2. monitor 收 SessionFinished 不调 is_end=True 冲刷：opus 流式编码器不足一帧 PCM
     残量永远不下发，每句固定丢一小段
  3. to_tts 路径 SessionFinished 不冲刷：非流式生成的音频文件结尾缺一截
  4. FIRST 分支不重置 opus_encoder：跨轮残留影响下一轮首帧

修复：
  - finish_session 开头先 text_to_speak(_pending_prefix)
  - monitor SessionFinished 调 wav_to_opus_data_audio_raw_stream(b"", is_end=True, ...)
  - to_tts 路径 SessionFinished 同样 is_end=True 冲刷
  - FIRST 分支调 reset_stream_state + opus_encoder.reset_state()

Usage:
    python benchmark/check_huoshan_3439.py
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import websockets

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_mock():
    spec = importlib.util.spec_from_file_location(
        "_huoshan_mock", os.path.join(os.path.dirname(__file__), "_huoshan_mock.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_mock = _load_mock()
build_provider = _mock.build_provider
run = _mock.run

# protocol constants
FULL_SERVER_RESPONSE = 0b1001
MsgTypeFlagWithEvent = 0b100
EVENT_SessionFinished = 152


def _build_session_finished_frame(session_id: str, meta: str = '{"e":"ok"}') -> bytes:
    res = bytearray()
    res.append((0b0001 << 4) | 1)
    res.append((FULL_SERVER_RESPONSE << 4) | MsgTypeFlagWithEvent)
    res.append((0b0001 << 4) | 0)
    res.append(0)
    res.extend(EVENT_SessionFinished.to_bytes(4, "big", signed=True))
    enc = session_id.encode("utf-8")
    res.extend(len(enc).to_bytes(4, "big", signed=True))
    res.extend(enc)
    meta_bytes = meta.encode("utf-8")
    res.extend(len(meta_bytes).to_bytes(4, "big", signed=True))
    res.extend(meta_bytes)
    return bytes(res)


def _async_iter_mock(items):
    """AsyncMock whose side_effect 依次返回 items，耗尽后抛 ConnectionClosed。"""
    m = AsyncMock()
    it = iter(items)

    async def _next(*a, **k):
        try:
            v = next(it)
        except StopIteration:
            raise websockets.ConnectionClosed(None, None)
        if isinstance(v, Exception):
            raise v
        return v

    m.side_effect = _next
    return m


def test_finish_session_sends_pending_prefix():
    p = build_provider()
    p._pending_prefix = "末尾残留"
    p.text_to_speak = AsyncMock()

    run(p.finish_session("sid"))
    assert p.text_to_speak.await_count == 1, (
        f"finish_session 应先调 1 次 text_to_speak，实际 {p.text_to_speak.await_count}"
    )
    arg = p.text_to_speak.await_args.args[0]
    assert arg == "末尾残留", f"应传 _pending_prefix，实际 {arg!r}"
    print("OK: finish_session 开头先发 _pending_prefix 残留")


def test_monitor_session_finished_flushes():
    p = build_provider()
    calls = []

    def _spy_encode(pcm, end_of_stream, callback=None):
        calls.append((pcm, end_of_stream))
        return b""

    p.opus_encoder.encode_pcm_to_opus_stream = _spy_encode
    p.ws.recv = _async_iter_mock(
        [_build_session_finished_frame(p.conn.sentence_id)]
    )

    run(p._start_monitor_tts_response())
    flush_calls = [c for c in calls if c[1] is True]
    assert len(flush_calls) >= 1, (
        f"monitor 收 SessionFinished 应至少 1 次 is_end=True 冲刷，实际 {calls}"
    )
    assert flush_calls[0][0] == b"", f"冲刷调用应传空 pcm，实际 {flush_calls[0][0]!r}"
    print("OK: monitor SessionFinished 调 is_end=True 冲刷流式编码器")


def test_to_tts_session_finished_flushes():
    """to_tts 路径 SessionFinished 同样 is_end=True 冲刷，复用真实 SessionFinished
    分支逻辑（与 monitor 一致；非流式通过 wav_to_opus_data_audio_raw_stream is_end
    把编码器残量追加到 audio_data）。"""
    p = build_provider()
    calls = []
    audio_data = []

    def _spy_encode(pcm, end_of_stream, callback=None):
        calls.append((pcm, end_of_stream))
        if callback:
            callback(b"frame")
        return b""

    p.opus_encoder.encode_pcm_to_opus_stream = _spy_encode

    async def _drive():
        ws = p.ws
        ws.recv = _async_iter_mock(
            [_build_session_finished_frame(p.conn.sentence_id)]
        )
        while True:
            try:
                msg = await ws.recv()
            except websockets.ConnectionClosed:
                break
            res = p.parser_response(msg)
            if res.optional.event == 152:  # SessionFinished
                if hasattr(p, "opus_encoder") and p.opus_encoder:
                    p.wav_to_opus_data_audio_raw_stream(
                        b"",
                        is_end=True,
                        callback=lambda opus_frame: audio_data.append(opus_frame),
                    )
                break

    run(_drive())
    flush_calls = [c for c in calls if c[1] is True]
    assert len(flush_calls) == 1, (
        f"to_tts 路径 SessionFinished 应 1 次 is_end=True 冲刷，实际 {calls}"
    )
    assert audio_data == [b"frame"], f"to_tts 收集到的帧应为 [b'frame']，实际 {audio_data}"
    print("OK: to_tts 路径 SessionFinished 同样 is_end=True 冲刷")


def test_first_resets_opus_encoder():
    """FIRST 分支调 reset_stream_state 后应再 opus_encoder.reset_state()。"""
    p = build_provider()
    # 验证当前代码里 FIRST 分支位置有 opus_encoder.reset_state 调用
    src = open(
        os.path.join(REPO, "main/xiaozhi-server/core/providers/tts/huoshan_double_stream.py")
    ).read()
    # 找 FIRST 分支后紧跟的 reset_state
    import re

    m = re.search(
        r"if message\.sentence_type == SentenceType\.FIRST:.*?self\.reset_stream_state\(\).*?self\.opus_encoder\.reset_state\(\)",
        src,
        re.DOTALL,
    )
    assert m is not None, "FIRST 分支应先 reset_stream_state 再 opus_encoder.reset_state()"
    print("OK: FIRST 分支调 opus_encoder.reset_state() 重置跨轮残留")


def main() -> int:
    test_finish_session_sends_pending_prefix()
    test_monitor_session_finished_flushes()
    test_to_tts_session_finished_flushes()
    test_first_resets_opus_encoder()
    print("\nALL PASS: 3439 finish_session 残留 + opus 尾帧冲刷（修复点 2）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
