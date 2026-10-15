"""声纹识别结果要同时保留 speaker_id 和展示名。"""
import aiohttp
import pytest

from core.utils.voiceprint_provider import (
    UNKNOWN_SPEAKER_NAME,
    VoiceprintProvider,
    resolve_speaker_identification,
)

SPEAKERS = {"test1": {"name": "张三", "description": "程序员"}}


def test_matched_speaker_keeps_id_and_name():
    identified = resolve_speaker_identification("test1", 0.91, SPEAKERS, 0.4)
    assert identified.speaker_id == "test1"
    assert identified.name == "张三"


def test_score_equal_to_threshold_still_matches():
    identified = resolve_speaker_identification("test1", 0.4, SPEAKERS, 0.4)
    assert identified.speaker_id == "test1"


def test_low_score_hides_id_and_uses_unknown_name():
    identified = resolve_speaker_identification("test1", 0.39, SPEAKERS, 0.4)
    assert identified.speaker_id is None
    assert identified.name == UNKNOWN_SPEAKER_NAME


def test_unconfigured_speaker_id_is_unknown():
    identified = resolve_speaker_identification("other", 0.99, SPEAKERS, 0.4)
    assert identified.speaker_id is None
    assert identified.name == UNKNOWN_SPEAKER_NAME


class _Response:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def json(self):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _Session:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        return self._response


def _enabled_provider():
    provider = VoiceprintProvider({})
    provider.enabled = True
    provider.api_url = "http://voiceprint.local/voiceprint/identify"
    provider.api_key = "k"
    provider.speaker_ids = ["test1"]
    provider.speaker_map = SPEAKERS
    provider.similarity_threshold = 0.4
    return provider


@pytest.mark.asyncio
async def test_identify_speaker_still_returns_display_name(monkeypatch):
    provider = _enabled_provider()
    monkeypatch.setattr(
        aiohttp,
        "ClientSession",
        lambda *args, **kwargs: _Session(
            _Response(200, {"speaker_id": "test1", "score": 0.88})
        ),
    )

    assert await provider.identify_speaker(b"wav", "session") == "张三"
    detail = await provider.identify_speaker_detail(b"wav", "session")
    assert detail.speaker_id == "test1"
    assert detail.name == "张三"


@pytest.mark.asyncio
async def test_identify_speaker_disabled_returns_none():
    provider = VoiceprintProvider({})
    assert await provider.identify_speaker(b"wav", "session") is None
    assert await provider.identify_speaker_detail(b"wav", "session") is None
