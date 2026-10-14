"""edge_tts Communicate.stream() 生产路径上 metadata patch 的集成测试。

不连 ws 服务。直接把 Communicate 实例的 mangled `__stream` 替换成 fake，
fake 内调真实的 `self.__parse_metadata(raw_bytes)` —— 这条路径正好走过
_install_metadata_patch 装在父类上的 wrapper。

之前 hotfix-3 ~ 5 的 SafeCommunicate 子类方案之所以假阳性，就是只测了
wrapper 自身，没走 stream() 入口。这层覆盖必须保留。

不依赖 pytest-asyncio（项目 conda env 没装），用 asyncio.run 在同步
测试里跑 async stream。
"""
from __future__ import annotations

import asyncio
from xml.sax.saxutils import escape

import edge_tts.communicate as ec
import edge_tts.exceptions


def _make_communicate() -> ec.Communicate:
    return ec.Communicate(text="hi", voice="zh-CN-XiaoxiaoNeural")


def _ok_payload(meta_type: str = "WordBoundary", offset: int = 12345, duration: int = 678, text: str = "你好") -> bytes:
    return (
        b'{"Metadata":[{"Type":"' + meta_type.encode() + b'",'
        b'"Data":{"Offset":' + str(offset).encode() + b','
        b'"Duration":' + str(duration).encode() + b','
        b'"text":{"Text":"' + escape(text).encode() + b'"}}}]}'
    )


def _install_fake_stream(comm: ec.Communicate, sequence: list) -> None:
    """在实例上替换 _Communicate__stream，绕过 aiohttp ws，按 sequence yield chunks。

    sequence 元素约定：
      - tuple ("raw_metadata", bytes) → 调 self.__parse_metadata(bytes) 并 yield 结果
      - dict → 直接 yield（audio 帧或其他）
      - "turn_end" → 模拟 turn.end：调 __compensate_offset 后退出
    """

    async def fake_stream(self):
        for item in sequence:
            if item == "turn_end":
                self._Communicate__compensate_offset()
                return
            if isinstance(item, tuple) and item[0] == "raw_metadata":
                _, raw = item
                # 显式 mangled name：fake_stream 在模块作用域定义，
                # `self.__parse_metadata` 不会被 Python 名字改写。
                parsed = self._Communicate__parse_metadata(raw)
                yield parsed
                self.state["last_duration_offset"] = (
                    parsed["offset"] + parsed["duration"]
                )
            else:
                yield item

    comm._Communicate__stream = fake_stream.__get__(comm, ec.Communicate)


def _drain_stream(comm: ec.Communicate) -> list:
    """同步跑一次 stream()，把 yield 出的 chunks 全收集。"""
    chunks: list = []

    async def collect():
        async for chunk in comm.stream():
            chunks.append(chunk)

    asyncio.run(collect())
    return chunks


class TestStreamMetadataPatch:
    def test_stream_skips_bad_metadata_then_yields_audio(self):
        """1 帧坏 metadata + 1 帧合法 audio → stream 不抛错，audio 拿到，坏帧计数==1。"""
        comm = _make_communicate()
        _install_fake_stream(comm, [
            ("raw_metadata", b"this is not json at all"),
            {"type": "audio", "data": b"\xff\xfb\x90\x00fake-mp3-bytes"},
            "turn_end",
        ])

        chunks = _drain_stream(comm)

        audio = [c for c in chunks if c.get("type") == "audio"]
        assert len(audio) == 1
        assert audio[0]["data"] == b"\xff\xfb\x90\x00fake-mp3-bytes"
        assert comm.state["bad_metadata_count"] == 1
        # 坏帧的 fallback offset=0 duration=0，last_duration_offset 走兜底 0+0
        assert comm.state["last_duration_offset"] == 0

    def test_stream_consecutive_bad_metadata_eventually_raises(self):
        """连续 6 帧坏 metadata → NoAudioReceived 冒泡，让 base.py 重试。"""
        comm = _make_communicate()
        bad = ("raw_metadata", b"not-json-again")
        sequence = [bad] * 6 + [
            {"type": "audio", "data": b"\xff\xfb"},
            "turn_end",
        ]
        _install_fake_stream(comm, sequence)

        async def run():
            async for _ in comm.stream():
                pass

        with pytest_raises_no_audio_received():
            asyncio.run(run())

        assert comm.state["bad_metadata_count"] == 6

    def test_stream_real_good_metadata_passes_through_unchanged(self):
        """正常 WordBoundary JSON → 不走 wrapper fallback 分支，原样 yield。"""
        comm = _make_communicate()
        _install_fake_stream(comm, [
            ("raw_metadata", _ok_payload("WordBoundary", 12345, 678, "你好")),
            {"type": "audio", "data": b"audio"},
            "turn_end",
        ])

        chunks = _drain_stream(comm)

        word = [c for c in chunks if c.get("type") == "WordBoundary"]
        assert len(word) == 1
        assert word[0]["offset"] == 12345
        assert word[0]["duration"] == 678
        assert word[0]["text"] == "你好"
        assert comm.state.get("bad_metadata_count", 0) == 0

    def test_stream_recovers_after_single_bad_frame(self):
        """1 帧坏 metadata 后 1 帧好 metadata → stream 继续，好帧原样 yield。"""
        comm = _make_communicate()
        _install_fake_stream(comm, [
            ("raw_metadata", b"junk"),
            ("raw_metadata", _ok_payload("WordBoundary", 9000, 400, "复")),
            {"type": "audio", "data": b"a"},
            "turn_end",
        ])

        chunks = _drain_stream(comm)

        word = [c for c in chunks if c.get("type") == "WordBoundary"]
        assert len(word) == 1
        assert word[0]["text"] == "复"
        assert comm.state["bad_metadata_count"] == 1


# pytest 没装 pytest-asyncio，pytest.raises 不认 coroutine；这里用上下文管理器
# 包一层，跟 pytest.raises 行为一致但能跑 coroutine。
import contextlib


@contextlib.contextmanager
def pytest_raises_no_audio_received():
    try:
        yield
    except edge_tts.exceptions.NoAudioReceived:
        return
    except BaseException as e:
        raise AssertionError(f"expected NoAudioReceived, got {type(e).__name__}: {e}")
    raise AssertionError("expected NoAudioReceived but no exception raised")
