"""PR-issue 3438 start_session 等 SessionStarted 确认回归测试。

复现：
  1. start_session 旧逻辑 send_event 后立即返回，文本线程不感知 SessionFailed / 超时
  2. 服务端 14s 内 26005 时整轮无声，无人感知

修复：
  - start_session 末尾 await asyncio.Future，monitor 收到 SessionStarted / SessionFailed
    时 set_result；超时报错让文本线程感知

Usage:
    python benchmark/check_huoshan_3438.py
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys

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


async def _set_result_later(p, value, delay=0.02):
    await asyncio.sleep(delay)
    if p._session_start_future and not p._session_start_future.done():
        p._session_start_future.set_result(value)


def test_session_started_success():
    p = build_provider()
    p.tts_timeout = 1.0

    async def _send_then_signal(*args, **kwargs):
        asyncio.create_task(_set_result_later(p, True, 0.02))

    async def _noop_conn(*a, **k):
        return None

    p.send_event = _send_then_signal
    p._ensure_connection = _noop_conn

    run(p.start_session("sid"))
    assert p._session_start_future is None, (
        "start_session 完成后 _session_start_future 应清空"
    )
    print("OK: SessionStarted 帧让 start_session 正常返回")


def test_session_failed_raises():
    p = build_provider()
    p.tts_timeout = 1.0

    async def _send_then_signal(*args, **kwargs):
        asyncio.create_task(_set_result_later(p, False, 0.02))

    async def _noop_conn(*a, **k):
        return None

    p.send_event = _send_then_signal
    p._ensure_connection = _noop_conn

    raised = False
    try:
        run(p.start_session("sid"))
    except RuntimeError as e:
        raised = True
        assert "SessionFailed" in str(e), f"异常文案应含 SessionFailed，实际 {e}"
    assert raised, "start_session 在 SessionFailed 时应 raise RuntimeError"
    print("OK: SessionFailed 帧让 start_session 抛 RuntimeError")


def test_session_timeout_raises():
    p = build_provider()
    p.tts_timeout = 0.1

    async def _send_no_signal(*args, **kwargs):
        pass

    async def _noop_conn(*a, **k):
        return None

    p.send_event = _send_no_signal
    p._ensure_connection = _noop_conn

    raised = False
    try:
        run(p.start_session("sid"))
    except (RuntimeError, asyncio.TimeoutError):
        raised = True
    assert raised, "start_session 在超时时应 raise"
    print("OK: start_session 超时抛错，文本线程能感知")


def main() -> int:
    test_session_started_success()
    test_session_failed_raises()
    test_session_timeout_raises()
    print("\nALL PASS: start_session 等 SessionStarted 确认（修复点 1）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
