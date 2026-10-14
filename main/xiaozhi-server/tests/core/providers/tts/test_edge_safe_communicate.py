"""edge_tts 父类 metadata 解析 monkey-patch 行为测试。

不连 edge_tts 服务，只验证 `_install_metadata_patch` 装在父类 mangled
方法上的 wrapper 自身行为契约。生产路径 stream() 上的兜底由
test_edge_metadata_patch_integration.py 单独覆盖。
"""
from __future__ import annotations

from xml.sax.saxutils import escape

import edge_tts.communicate as ec
import edge_tts.exceptions
import pytest

from core.providers.tts.edge import _PARSED_METADATA_ATTR, _METADATA_FALLBACK_COUNT


def _make_communicate() -> ec.Communicate:
    return ec.Communicate(text="hi", voice="zh-CN-XiaoxiaoNeural")


def _ok_payload(meta_type: str = "WordBoundary", offset: int = 8000, duration: int = 2500) -> bytes:
    return (
        b'{"Metadata":[{"Type":"' + meta_type.encode() + b'",'
        b'"Data":{"Offset":' + str(offset).encode() + b','
        b'"Duration":' + str(duration).encode() + b','
        b'"text":{"Text":"' + escape("hi").encode() + b'"}}}]}'
    )


class TestSafeParseMetadata:
    def test_a_normal_word_boundary_returns_full_metadata(self):
        """正常 WordBoundary JSON → 返回原 metadata dict，不增加 bad_metadata_count。"""
        comm = _make_communicate()
        result = comm._Communicate__parse_metadata(_ok_payload("WordBoundary", 8000, 2500))
        assert result["type"] == "WordBoundary"
        assert result["offset"] == 8000
        assert result["duration"] == 2500
        assert result["text"] == "hi"
        assert comm.state.get("bad_metadata_count", 0) == 0

    def test_a_sentence_boundary(self):
        comm = _make_communicate()
        result = comm._Communicate__parse_metadata(_ok_payload("SentenceBoundary", 1000, 500))
        assert result["type"] == "SentenceBoundary"
        assert result["offset"] == 1000
        assert result["duration"] == 500

    def test_b_bad_bytes_returns_safe_fallback_and_increments(self):
        """非 JSON bytes → 返回 safe fallback + bad_metadata_count==1。"""
        comm = _make_communicate()
        result = comm._Communicate__parse_metadata(b"this is not json {")
        assert result == {
            "type": "metadata_ignored",
            "offset": 0,
            "duration": 0,
            "text": "",
        }
        assert comm.state["bad_metadata_count"] == 1

    def test_b_empty_bytes(self):
        comm = _make_communicate()
        result = comm._Communicate__parse_metadata(b"")
        assert result["type"] == "metadata_ignored"
        assert comm.state["bad_metadata_count"] == 1

    def test_c_six_consecutive_bad_bytes_raises_no_audio(self):
        """连续 6 次非 JSON bytes → 第 6 次 raise NoAudioReceived。"""
        comm = _make_communicate()
        for _ in range(_METADATA_FALLBACK_COUNT):
            r = comm._Communicate__parse_metadata(b"bad")
            assert r["type"] == "metadata_ignored"
        assert comm.state["bad_metadata_count"] == _METADATA_FALLBACK_COUNT
        with pytest.raises(edge_tts.exceptions.NoAudioReceived):
            comm._Communicate__parse_metadata(b"bad again")

    def test_f_non_utf8_bytes_returns_safe_fallback(self):
        """非 utf-8 bytes → 走 safe fallback + bad_metadata_count+=1。"""
        comm = _make_communicate()
        result = comm._Communicate__parse_metadata(b"\x00\xff\xfe")
        assert result == {
            "type": "metadata_ignored",
            "offset": 0,
            "duration": 0,
            "text": "",
        }
        assert comm.state["bad_metadata_count"] == 1

    def test_g_missing_metadata_key_raises_keyerror(self):
        """合法 JSON 缺 Metadata 字段 → KeyError 透出，不被吞。"""
        comm = _make_communicate()
        with pytest.raises(KeyError):
            comm._Communicate__parse_metadata(b'{"type": "test"}')
        assert comm.state.get("bad_metadata_count", 0) == 0


class TestPatchInstallation:
    def test_install_replaces_mangled_attr_on_communicate_class(self):
        """_install_metadata_patch 跑过之后，父类 mangled attr 已被替换成 wrapper。"""
        cls = ec.Communicate
        current = cls.__dict__.get(_PARSED_METADATA_ATTR)
        assert callable(current)
        # wrapper 内层捕获 json.JSONDecodeError，可由坏字节验证它已装上
        comm = _make_communicate()
        result = comm._Communicate__parse_metadata(b"definitely-not-json")
        assert result["type"] == "metadata_ignored"
