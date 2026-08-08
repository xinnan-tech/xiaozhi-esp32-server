"""Regression tests for ``_get_segment_text`` boundary selection.

The first sentence should split at the *earliest* punctuation boundary (lowest
time-to-first-audio); subsequent sentences should split at the *latest* boundary
(largest chunk, fewer TTS calls). The pre-fix code used ``rfind`` for every
sentence and kept the smallest position, which is neither.

``_get_segment_text`` advances ``processed_chars`` to just past the chosen
boundary, so asserting on ``processed_chars`` pins the boundary deterministically
without depending on the punctuation-stripping helper.

Self-contained: no conftest required.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from core.providers.tts.base import TTSProviderBase  # noqa: E402


class _StubTTS(TTSProviderBase):
    async def text_to_speak(self, text, output_file):  # pragma: no cover - abstract stub
        return None


def _make(text, is_first_sentence):
    obj = object.__new__(_StubTTS)
    obj.tts_text_buff = [text]
    obj.processed_chars = 0
    obj.is_first_sentence = is_first_sentence
    obj.tts_stop_request = False
    obj.first_sentence_punctuations = ("，", ",", "。", "？", "?", "！", "!", "；", ";", "：")
    obj.punctuations = ("。", "？", "?", "！", "!", "；", ";", "：")
    return obj


def test_first_sentence_splits_at_earliest_boundary():
    # "a, b, c." — earliest punctuation is the first comma at index 1.
    obj = _make("a, b, c.", is_first_sentence=True)
    segment = obj._get_segment_text()
    assert segment is not None
    assert obj.processed_chars == 2  # consumed "a,"
    assert obj.is_first_sentence is False  # flag flips after the first split


def test_later_sentence_splits_at_latest_boundary():
    # "one. two? three!" — latest punctuation is the trailing "!" at index 15.
    obj = _make("one. two? three!", is_first_sentence=False)
    segment = obj._get_segment_text()
    assert segment is not None
    assert obj.processed_chars == 16  # consumed the whole span up to the last "!"


def test_no_boundary_returns_none():
    obj = _make("no punctuation here", is_first_sentence=False)
    assert obj._get_segment_text() is None
