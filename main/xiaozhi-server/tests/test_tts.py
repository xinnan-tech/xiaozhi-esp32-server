"""TTS (Speech Synthesis) pipeline test.

Mock mode (default): Constructs real TTS provider using config from data/.config.yaml;
All external HTTP/SDK calls use the shim injected by conftest; no real requests are sent.
Live mode (``RUN_LIVE_API_TESTS=1``): call real TTS provider.

Interface contract (core/providers/tts/base.py):
    text_to_speak(text, output_file) -> Async, write synthesis result to output_file

Note:
- 3 constructor tests do not depend on cloud services; the 4th is test_tts_text_to_speak_writes_nonempty_file
  This is a real link test, it will actually send HTTP.
- In Mock mode: the 4th test assertion is lenient - file existence is sufficient (shim creates empty file),
  Do not strictly require size > 0. Strictly validate size > 0 in Live mode.
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
    LIVE_API_TESTS,
    get_provider_config,
    get_provider_type,
    get_selected_provider_name,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _build_provider():
    name = get_selected_provider_name("TTS")
    if not name:
        pytest.skip("selected_module.TTS not set")
    cfg = get_provider_config("TTS", name)
    if not cfg:
        pytest.skip(f"TTS provider '{name}' configuration missing")
    ptype = get_provider_type("TTS", name)
    if not ptype:
        pytest.skip(f"Missing type field for TTS '{name}'")
    from core.utils.tts import create_instance

    return create_instance(ptype, cfg, True)


def test_tts_provider_constructs_from_config() -> None:
    """Should be able to instantiate a TTSProviderBase subclass from config."""
    provider = _build_provider()
    from core.providers.tts.base import TTSProviderBase

    assert isinstance(provider, TTSProviderBase), (
        f"Invalid TTS provider type: {type(provider).__name__}"
    )


def test_tts_provider_exposes_to_tts() -> None:
    """provider must implement either to_tts or to_tts_stream."""
    provider = _build_provider()
    has_sync = hasattr(provider, "to_tts") and callable(provider.to_tts)
    has_stream = hasattr(provider, "to_tts_stream") and callable(
        provider.to_tts_stream
    )
    assert has_sync or has_stream, (
        f"{type(provider).__name__} missing to_tts / to_tts_stream methods"
    )


def test_tts_provider_has_output_dir() -> None:
    """provider should have an output_file attribute (where synthesis results are written)."""
    provider = _build_provider()
    assert hasattr(provider, "output_file"), (
        f"{type(provider).__name__} missing output_file attribute"
    )
    assert isinstance(provider.output_file, str)
    assert provider.output_file, "output_file must not be empty"


def test_tts_text_to_speak_writes_file() -> None:
    """Mock mode: assert file exists. Live mode: assert size > 0.

    Refer to the implementation of performance_tester_tts.py:
    - mock conn(sample_rate/audio_format/stop_event/client_abort/headers)
      and opus_encoder (SimpleNamespace placeholder is sufficient)
    - generate_filename() retrieves the output path
    - text_to_speak() asynchronously calls cloud service, writes file
    - 10s timeout
    - Delete test files after use to avoid cluttering the tmp/ directory
    """
    provider = _build_provider()

    # See performance_tester_tts.py: some providers internally access self.conn.sample_rate, etc.
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
                provider.text_to_speak("Test it", out_file),
                timeout=10.0,
            )

        asyncio.run(run())

        assert os.path.exists(out_file), f"Output file does not exist: {out_file}"
        if LIVE_API_TESTS:
            assert os.path.getsize(out_file) > 0, f"Output file is empty: {out_file}"
    finally:
        if os.path.exists(out_file):
            try:
                os.remove(out_file)
            except OSError:
                pass
