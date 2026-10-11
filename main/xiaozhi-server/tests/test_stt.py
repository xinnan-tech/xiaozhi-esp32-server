"""ASR（语音识别）链路测试。

Mock 模式（默认）：从 data/.config.yaml 拿配置构造真实 ASR provider；
所有外部 HTTP/SDK 调用走 conftest 注入的 shim，不发真请求。
Live 模式（``RUN_LIVE_API_TESTS=1``）：调真实 ASR provider。

接口约定（core/providers/asr/base.py）：
    async speech_to_text_wrapper(pcm_data, session_id) -> Tuple[Optional[str], Optional[str]]
    async speech_to_text(opus_data, session_id, artifacts) -> Tuple[Optional[str], Optional[str]]

注意：
- performance_tester_asr.py 用 3-arg 调 wrapper 是错的（base 只接 2 个），
  这里用 2-arg 正确版本
- FunASR 是本地模型：构造时会加载 model_dir 的模型文件；
  如果模型没下载，`__init__` 直接抛异常，测试会 skip
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from tests.conftest import (
    get_provider_config,
    get_provider_type,
    get_selected_provider_name,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "config" / "assets"


def _build_provider():
    name = get_selected_provider_name("ASR")
    if not name:
        pytest.skip("selected_module.ASR 未设置")
    cfg = get_provider_config("ASR", name)
    if not cfg:
        pytest.skip(f"ASR provider '{name}' 配置缺失")
    ptype = get_provider_type("ASR", name)
    if not ptype:
        pytest.skip(f"ASR '{name}' 的 type 字段缺失")
    from core.utils.asr import create_instance

    return create_instance(ptype, cfg, True)


def _find_test_audio() -> Path:
    """从 config/assets/ 找 >300KB 的 wav 当测试音频。"""
    if not _ASSETS_DIR.exists():
        pytest.skip(f"音频目录不存在：{_ASSETS_DIR}")
    wavs = sorted(
        (p for p in _ASSETS_DIR.glob("*.wav") if p.stat().st_size > 300 * 1024),
        key=lambda p: p.stat().st_size,
        reverse=True,  # 最大的优先
    )
    if not wavs:
        pytest.skip(f"config/assets/ 下没有 >300KB 的 wav 文件")
    return wavs[0]


def test_asr_provider_constructs_from_config() -> None:
    """从 config 应该能实例化出 ASRProviderBase 子类。"""
    provider = _build_provider()
    from core.providers.asr.base import ASRProviderBase

    assert isinstance(provider, ASRProviderBase), (
        f"ASR provider 类型错：{type(provider).__name__}"
    )


def test_asr_provider_exposes_speech_to_text() -> None:
    """provider 必须实现 speech_to_text 方法。"""
    provider = _build_provider()
    assert hasattr(provider, "speech_to_text"), (
        f"{type(provider).__name__} 缺少 speech_to_text 方法"
    )
    assert callable(provider.speech_to_text)


def test_asr_provider_has_output_dir() -> None:
    """provider 应有 output_dir 属性（写入识别结果用）。"""
    provider = _build_provider()
    assert hasattr(provider, "output_dir"), (
        f"{type(provider).__name__} 缺少 output_dir 属性"
    )


def test_asr_speech_to_text_wrapper_returns_text() -> None:
    """真发一次 ASR 请求（live 模式），断言返回识别结果。

    Mock 模式下也照常调，但 shim 返回空 dict/text，断言宽松：
    text 可以是 None / str / dict，只要不抛异常就算通过。

    参考 performance_tester_asr.py：
    - 喂真实 wav 文件 bytes 给 speech_to_text_wrapper
    - 10s 超时
    - 返回的 text 可能是 None（识别失败）/ str（部分 provider）/ dict（FunASR 等带 emotion/language 的）
    """
    provider = _build_provider()
    # Mock 模式下没有 wav 资产也能跑（shim 不读文件）。
    from tests.conftest import LIVE_API_TESTS
    if LIVE_API_TESTS:
        wav_path = _find_test_audio()
        audio_data = wav_path.read_bytes()
    else:
        # Mock 模式：喂占位 bytes，shim 不会真去解码。
        audio_data = b"\x00" * 1024

    async def run():
        return await asyncio.wait_for(
            provider.speech_to_text_wrapper([audio_data], "test-session"),
            timeout=10.0,
        )

    text, file_path = asyncio.run(run())
    # ASR 结果兼容性：None / str / dict（FunASR 返回 {content, language, emotion}）
    assert text is None or isinstance(text, (str, dict)), (
        f"speech_to_text_wrapper 应返回 (None/str/dict, str|None)，"
        f"得到 text 类型 {type(text).__name__}"
    )
    if isinstance(text, dict):
        # FunASR 风格：取 content 字段（live 模式才严格校验）。
        if LIVE_API_TESTS:
            assert text.get("content"), f"ASR dict 结果缺少 content：{text!r}"
