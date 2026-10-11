"""ASR (Speech Recognition) pipeline test.

Mock mode (default): Constructs real ASR provider using config from data/.config.yaml;
All external HTTP/SDK calls use the shim injected by conftest; no real requests are sent.
Live mode (``RUN_LIVE_API_TESTS=1``): call real ASR provider.

Interface contract (core/providers/asr/base.py):
    async speech_to_text_wrapper(pcm_data, session_id) -> Tuple[Optional[str], Optional[str]]
    async speech_to_text(opus_data, session_id, artifacts) -> Tuple[Optional[str], Optional[str]]

Note:
- performance_tester_asr.py calling wrapper with 3 args is incorrect (base accepts only 2),
  Use correct 2-arg version here
- FunASR is a local model: it loads model files from model_dir during construction;
  If the model is not downloaded, `__init__` throws an exception directly, causing tests to skip
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
        pytest.skip("selected_module.ASR not set")
    cfg = get_provider_config("ASR", name)
    if not cfg:
        pytest.skip(f"ASR provider '{name}' configuration missing")
    ptype = get_provider_type("ASR", name)
    if not ptype:
        pytest.skip(f"ASR '{name}' missing type field")
    from core.utils.asr import create_instance

    return create_instance(ptype, cfg, True)


def _find_test_audio() -> Path:
    """Find a wav file >300KB from config/assets/ as test audio."""
    if not _ASSETS_DIR.exists():
        pytest.skip(f"Audio directory does not exist: {_ASSETS_DIR}")
    wavs = sorted(
        (p for p in _ASSETS_DIR.glob("*.wav") if p.stat().st_size > 300 * 1024),
        key=lambda p: p.stat().st_size,
        reverse=True,  # Highest priority
    )
    if not wavs:
        pytest.skip(f"No wav files >300KB in config/assets/")
    return wavs[0]


def test_asr_provider_constructs_from_config() -> None:
    """Should be able to instantiate an ASRProviderBase subclass from config."""
    provider = _build_provider()
    from core.providers.asr.base import ASRProviderBase

    assert isinstance(provider, ASRProviderBase), (
        f"Invalid ASR provider type: {type(provider).__name__}"
    )


def test_asr_provider_exposes_speech_to_text() -> None:
    """provider must implement the speech_to_text method."""
    provider = _build_provider()
    assert hasattr(provider, "speech_to_text"), (
        f"{type(provider).__name__} missing speech_to_text method"
    )
    assert callable(provider.speech_to_text)


def test_asr_provider_has_output_dir() -> None:
    """provider should have an output_dir attribute (for writing recognition results)."""
    provider = _build_provider()
    assert hasattr(provider, "output_dir"), (
        f"{type(provider).__name__} missing output_dir attribute"
    )


def test_asr_speech_to_text_wrapper_returns_text() -> None:
    """Send one real ASR request (live mode), assert recognition result is returned.

    In Mock mode, calls proceed normally, but the shim returns an empty dict/text; assertions are lenient:
    text can be None / str / dict; passes if no exception is raised.

    See performance_tester_asr.py:
    - Feed real wav file bytes to speech_to_text_wrapper
    - 10s timeout
    - Returned text may be None (recognition failure) / str (some providers) / dict (FunASR etc. with emotion/language)
    """
    provider = _build_provider()
    # Mock mode runs without wav assets (shim does not read files).
    from tests.conftest import LIVE_API_TESTS
    if LIVE_API_TESTS:
        wav_path = _find_test_audio()
        audio_data = wav_path.read_bytes()
    else:
        # Mock mode: Feed placeholder bytes; shim will not actually decode.
        audio_data = b"\x00" * 1024

    async def run():
        return await asyncio.wait_for(
            provider.speech_to_text_wrapper([audio_data], "test-session"),
            timeout=10.0,
        )

    text, file_path = asyncio.run(run())
    # ASR result compatibility: None / str / dict (FunASR returns {content, language, emotion})
    assert text is None or isinstance(text, (str, dict)), (
        f"speech_to_text_wrapper should return (None/str/dict, str|None),"
        f"Obtained text type {type(text).__name__}"
    )
    if isinstance(text, dict):
        # FunASR style: extract content field (strict validation only in live mode).
        if LIVE_API_TESTS:
            assert text.get("content"), f"ASR dict result missing content:{text!r}"
