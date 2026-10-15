"""PR #3442 metadata patch reload 嵌套回归测试。

复现 pr02 第三轮 P2：模拟 `importlib.reload` 后旧 wrapper（W1）嵌套在新
wrapper（W2）内。W1 自身返回 fake metadata_ignored dict，W2 在 success
路径上比较 partial_text 不等于 "" 立即 reset 计数，5 阈值永远到不了。

验证：
  1. reload 后 __wrapped__ 解套（不嵌套 W1），NoAudioReceived 能在 5 次
     坏帧后正常 raise
  2. wrapper 内部 metadata_ignored fake 帧不会触发 partial_text reset

Usage:
    python benchmark/check_metadata_patch_reload.py
"""

from __future__ import annotations

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(REPO, "main", "xiaozhi-server")
if SERVER not in sys.path:
    sys.path.insert(0, SERVER)

import edge_tts  # noqa: E402
import edge_tts.communicate  # noqa: E402

from core.providers.tts import edge  # noqa: E402


def _make_bad_original():
    def bad_original(self, data):
        raise json.JSONDecodeError("forced bad frame", "x", 0)

    return bad_original


def _make_good_original(text_seq):
    it = iter(text_seq)

    def good_original(self, data):
        try:
            t = next(it)
        except StopIteration:
            t = "end"
        return {"type": "WordBoundary", "offset": 0, "duration": 0, "text": t}

    return good_original


class FakeComm:
    def __init__(self):
        self.state = {}


def test_no_audio_received_raises_after_reload():
    """reload 解套后 5 次连续坏帧应能 raise NoAudioReceived。"""
    cls = edge_tts.communicate.Communicate
    edge._metadata_wrapper.__wrapped__ = _make_bad_original()
    edge._install_metadata_patch()
    assert cls.__dict__[edge._PARSED_METADATA_ATTR] is edge._metadata_wrapper

    # 模拟 reload：再次调 _install_metadata_patch，原 bad_original 应被解套
    # 沿 __wrapped__ 链追到 bad_original，新 wrapper.__wrapped__ = bad_original
    bad2 = _make_bad_original()
    edge._metadata_wrapper.__wrapped__ = bad2
    edge._install_metadata_patch()
    current = cls.__dict__[edge._PARSED_METADATA_ATTR]
    assert current is edge._metadata_wrapper
    assert edge._metadata_wrapper.__wrapped__ is bad2

    fc = FakeComm()
    raised = False
    for _ in range(10):
        try:
            edge._metadata_wrapper(fc, "bad")
        except edge_tts.exceptions.NoAudioReceived:
            raised = True
            break
    assert raised, "reload 后 10 次坏帧没 raise NoAudioReceived"


def test_metadata_ignored_fake_does_not_reset():
    """wrapper 自身产出的 metadata_ignored fake 帧不触发 partial_text reset。"""
    cls = edge_tts.communicate.Communicate
    good = _make_good_original(["hello"] * 20)
    edge._metadata_wrapper.__wrapped__ = good
    edge._install_metadata_patch()

    fc = FakeComm()
    bad = _make_bad_original()
    edge._metadata_wrapper.__wrapped__ = bad
    for _ in range(5):
        try:
            edge._metadata_wrapper(fc, "bad")
        except edge_tts.exceptions.NoAudioReceived:
            pass
    assert fc.state.get("bad_metadata_count", 0) == 5, (
        f"bad_metadata_count 期望 5，实际 {fc.state.get('bad_metadata_count', 0)}"
    )

    # 关键：用 good_original 返回 hello，count 应清零（真 partial_text 变更）
    edge._metadata_wrapper.__wrapped__ = good
    edge._metadata_wrapper(fc, "good")
    assert fc.state.get("bad_metadata_count", 0) == 0, (
        f"good 帧后 count 应清零到 0，实际 {fc.state.get('bad_metadata_count', 0)}"
    )

    edge._metadata_wrapper.__wrapped__ = bad
    try:
        edge._metadata_wrapper(fc, "bad")
    except edge_tts.exceptions.NoAudioReceived:
        pass
    assert fc.state.get("bad_metadata_count", 0) == 1


def main() -> int:
    test_no_audio_received_raises_after_reload()
    print("OK: reload 解套后 5 次坏帧能 raise NoAudioReceived")
    test_metadata_ignored_fake_does_not_reset()
    print("OK: metadata_ignored fake 帧不触发 partial_text reset")
    return 0


if __name__ == "__main__":
    sys.exit(main())
