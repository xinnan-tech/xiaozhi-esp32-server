"""TTS（语音合成）链路测试。

从 data/.config.yaml 拿配置，调真实 TTS provider。

接口约定（core/providers/tts/base.py）：
    text_to_speak(text, output_file) -> 异步，把合成结果写到 output_file

参考项目自带的 performance_tester_tts.py 模式：
- 必须 mock self.conn 和 self.opus_encoder（base 默认是 None，
  但某些 TTS 实现内部访问 self.conn.sample_rate 会 AttributeError）
- generate_filename() 拿输出路径（EdgeTTS 默认 .mp3，其他 provider 默认 .wav）
- text_to_speak() 异步写文件，10s 超时防卡死
- 真发请求走云服务（EdgeTTS 免认证走微软公共 endpoint，其他 provider 要 key）

注意：3 个构造测试不依赖云服务；第 4 个 test_tts_text_to_speak_writes_nonempty_file
才是真链路测试，会真发 HTTP。
"""
from __future__ import annotations

import asyncio
import os
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.conftest import (
    get_provider_config,
    get_provider_type,
    get_selected_provider_name,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _build_provider():
    name = get_selected_provider_name("TTS")
    if not name:
        pytest.skip("selected_module.TTS 未设置")
    cfg = get_provider_config("TTS", name)
    if not cfg:
        pytest.skip(f"TTS provider '{name}' 配置缺失")
    ptype = get_provider_type("TTS", name)
    if not ptype:
        pytest.skip(f"TTS '{name}' 的 type 字段缺失")
    from core.utils.tts import create_instance

    return create_instance(ptype, cfg, True)


def test_tts_provider_constructs_from_config() -> None:
    """从 config 应该能实例化出 TTSProviderBase 子类。"""
    provider = _build_provider()
    from core.providers.tts.base import TTSProviderBase

    assert isinstance(provider, TTSProviderBase), (
        f"TTS provider 类型错：{type(provider).__name__}"
    )


def test_tts_provider_exposes_to_tts() -> None:
    """provider 必须实现 to_tts / to_tts_stream 之一。"""
    provider = _build_provider()
    has_sync = hasattr(provider, "to_tts") and callable(provider.to_tts)
    has_stream = hasattr(provider, "to_tts_stream") and callable(
        provider.to_tts_stream
    )
    assert has_sync or has_stream, (
        f"{type(provider).__name__} 缺少 to_tts / to_tts_stream 方法"
    )


def test_tts_provider_has_output_dir() -> None:
    """provider 应有 output_file 属性（合成结果写到哪）。"""
    provider = _build_provider()
    assert hasattr(provider, "output_file"), (
        f"{type(provider).__name__} 缺少 output_file 属性"
    )
    assert isinstance(provider.output_file, str)
    assert provider.output_file, "output_file 不应为空"


def test_tts_text_to_speak_writes_nonempty_file() -> None:
    """真发一次 TTS 请求到云服务，断言输出文件存在 + size > 0。

    参考 performance_tester_tts.py 的实现：
    - mock conn（sample_rate/audio_format/stop_event/client_abort/headers）
      和 opus_encoder（SimpleNamespace 占位即可）
    - generate_filename() 拿输出路径
    - text_to_speak() 异步调云服务，写文件
    - 10s 超时
    - 用完删掉测试文件，避免 tmp/ 目录堆积

    EdgeTTS：走微软公共 endpoint，无需 api_key。
    其他 provider：需要 data/.config.yaml 配 key，否则网络/认证失败会 skip。
    """
    provider = _build_provider()

    # 参考 performance_tester_tts.py：部分 provider 内部访问 self.conn.sample_rate 等
    if not hasattr(provider, "conn") or provider.conn is None:
        provider.conn = SimpleNamespace(
            sample_rate=16000,
            audio_format="pcm",
            stop_event=threading.Event(),
            client_abort=False,
            headers={},
        )
    if not hasattr(provider, "opus_encoder") or provider.opus_encoder is None:
        provider.opus_encoder = SimpleNamespace()

    out_file = provider.generate_filename()
    try:
        async def run():
            await asyncio.wait_for(
                provider.text_to_speak("测试一下", out_file),
                timeout=10.0,
            )

        asyncio.run(run())

        assert os.path.exists(out_file), f"输出文件不存在：{out_file}"
        assert os.path.getsize(out_file) > 0, f"输出文件为空：{out_file}"
    finally:
        if os.path.exists(out_file):
            try:
                os.remove(out_file)
            except OSError:
                pass
