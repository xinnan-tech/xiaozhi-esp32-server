"""TTSProviderBase._get_segment_text must not cut sentences inside quotes."""
import pytest

from core.providers.tts.base import TTSProviderBase


class _TTS(TTSProviderBase):
    async def text_to_speak(self, text, output_file):
        return None


def _segments(text, step, first_sentence=False):
    tts = object.__new__(_TTS)
    tts.punctuations = ("。", "？", "?", "！", "!", "；", ";", "：")
    tts.first_sentence_punctuations = ("，", "~", "、", ",") + tts.punctuations
    tts.tts_text_buff, tts.processed_chars = [], 0
    tts.is_first_sentence, tts.tts_stop_request = first_sentence, False
    out = []
    for i in range(0, len(text), step):
        tts.tts_text_buff.append(text[i:i + step])
        segment = tts._get_segment_text()
        if segment:
            out.append(segment)
    tts.tts_stop_request = True
    rest = tts._get_segment_text()
    if rest:
        out.append(rest)
    return out


@pytest.mark.parametrize("step", [1, 3, 7])
def test_japanese_quote_followed_by_tte_stays_whole(step):
    assert _segments("思わず「わぁ！」って声が出たんだ。きみは？", step) == [
        "思わず「わぁ！」って声が出たんだ",
        "きみは？",
    ]


@pytest.mark.parametrize("step", [1, 4])
def test_chinese_quote_followed_by_speaker_stays_whole(step):
    segments = _segments("他大声说：“好！”然后笑了。", step)
    assert not any(seg.startswith("”") for seg in segments)
    # the leading “ is stripped by textUtils, the closing ” must stay with its sentence
    assert any("好！”然后笑了" in seg for seg in segments)


@pytest.mark.parametrize("step", [1, 5])
def test_closing_quote_then_period_is_not_left_alone(step):
    assert _segments("「すごい！」。次はね、雨！", step) == ["「すごい！」", "次はね、雨"]


@pytest.mark.parametrize("step", [1, 5])
def test_text_without_quotes_is_split_as_before(step):
    assert _segments("普通の文。次の文！最後", step) == ["普通の文", "次の文", "最後"]


def test_first_sentence_still_splits_at_comma():
    assert _segments("そっか、実習で疲れたんだね。", 1, first_sentence=True)[0] == "そっか"
