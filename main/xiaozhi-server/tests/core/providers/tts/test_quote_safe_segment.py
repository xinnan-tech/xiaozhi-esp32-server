"""TTSProviderBase._get_segment_text must not cut sentences inside quotes."""
import pytest

from core.providers.tts.base import TTSProviderBase
from core.utils import textUtils


# 最小 stub：仅需满足抽象方法实例化要求；object.__new__ 会绕过
# abstractmethod 检查，若基类新增抽象方法这里不会自动报错，属预期（测试不调用）
class _TTS(TTSProviderBase):
    async def text_to_speak(self, text, output_file):
        return None


def _segments(text, step, first_sentence=False):
    """按 step 切片喂入，返回切出的各段。

    与真实调用保持一致：每来一个 chunk 循环调用 _get_segment_text 直到切不出，
    结束时剩余文本由 _process_remaining_text_stream 一次性发出。
    """
    tts = object.__new__(_TTS)
    tts.punctuations = ("。", "？", "?", "！", "!", "；", ";", "：")
    tts.first_sentence_punctuations = ("，", "~", "、", ",") + tts.punctuations
    tts.tts_text_buff, tts.processed_chars = [], 0
    tts.is_first_sentence = first_sentence
    out = []
    for i in range(0, len(text), step):
        tts.tts_text_buff.append(text[i:i + step])
        while True:
            segment = tts._get_segment_text()
            if not segment:
                break
            out.append(segment)
    # 剩余文本一次性发出，不再切分
    full_text = "".join(tts.tts_text_buff)
    remaining = full_text[tts.processed_chars:]
    if remaining:
        rest = textUtils.get_string_no_punctuation_or_emoji(remaining)
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


@pytest.mark.parametrize("step", [1, 4])
def test_ascii_quote_at_stream_end_stays_whole(step):
    # 等待引号闭合，整句一次输出；flush 段尾部标点会被剥掉
    assert _segments('She said, "Hi!"', step) == ['She said, "Hi']


_LQ, _RQ = "\u00ab", "\u00bb"        # « » 法/俄语书名号式引号
_GOPEN, _GCLOSE = "\u201e", "\u201c"  # „ “ 德语低引号


@pytest.mark.parametrize("step", [1, 4])
def test_guillemets_are_not_split(step):
    # ！ 位于 «» 内，须等右书名号闭合后在句尾标点处切分
    text = "Il a dit " + _LQ + "Bonjour ! " + _RQ + " puis est parti."
    assert _segments(text, step) == [text[:-1]]


@pytest.mark.parametrize("step", [1, 4])
def test_german_low9_quotes_stay_whole(step):
    # „…“ 的闭合符 “ 是中文引号的开引号：“ 总被 (“”, ””) 对计为 opener，
    # 故 „…“ 闭合后依然判不平衡，无论后续有无句末标点（实测），
    # 德语只能整句 stop flush —— 这是字符冲突下的保守预期，非缺陷
    text = "Er sagte " + _GOPEN + "Hallo!" + _GCLOSE + " und ging."
    assert _segments(text, step) == [text[:-1]]
    # 闭合 + 中文句号同样整句 flush：正路径因 “ 双重语义不可达
    text2 = "Er sagte " + _GOPEN + "Hallo!" + _GCLOSE + "。Dann geht er。"
    assert _segments(text2, step) == [text2[:-1]]


@pytest.mark.parametrize("step", [1, 4])
def test_unterminated_quote_flushes_on_stop(step):
    # 单个引号符号（未闭合）不卡死；行首的 " 属于标点，flush 时会被剥掉
    assert _segments('"Hi', step) == ["Hi"]
    assert _segments("「わぁ", step) == ["「わぁ"]


_LB, _RB = "\u3010", "\u3011"  # 【】


@pytest.mark.parametrize("step", [1, 4])
def test_brackets_with_punct_inside_are_not_split(step):
    # ！位于【】内不得切开（切开时第一段只到“他说【重要”），
    # 应等右括号闭合后在句尾标点切分
    assert _segments("他说" + _LB + "重要！步骤" + _RB + "。然后走了。", step) == [
        "他说" + _LB + "重要！步骤",
        "然后走了",
    ]


def test_nested_mixed_quotes_stay_whole():
    # 嵌套引号逐对独立计数，互不干扰
    assert _segments("“他说『好』了。”然后离开。", 1) == ["他说『好』了。”然后离开"]


def test_apostrophes_do_not_block_splitting():
    # 单引号有撇号歧义（don't），不得纳入平衡检查；flush 段尾部标点会被剥掉
    assert _segments("don't! It's fine.", 1) == ["don't", "It's fine"]


def test_first_sentence_still_splits_at_comma():
    assert _segments("そっか、実習で疲れたんだね。", 1, first_sentence=True)[0] == "そっか"


@pytest.mark.parametrize("step", range(1, 14))
def test_thousands_separator_is_not_a_first_sentence_break(step):
    # 第一句会在逗号处切，但 1,280 / 1，280 里的逗号是数字的一部分
    assert _segments("一共1,280元，请查收。", step, first_sentence=True) == [
        "一共1,280元",
        "请查收",
    ]
    assert _segments("一共1，280元。请查收。", step, first_sentence=True) == [
        "一共1，280元",
        "请查收",
    ]


@pytest.mark.parametrize("step", range(1, 14))
def test_fullwidth_time_colon_stays_with_the_minutes(step):
    # ： 在默认断句集里；15：30 不能切成「现在是15」和「30」
    assert _segments("现在是15：30。请出门。", step) == ["现在是15：30", "请出门"]


@pytest.mark.parametrize("step", range(1, 12))
def test_fullwidth_colon_after_numeric_label_still_breaks(step):
    assert _segments("提示1：请出门。现在走。", step) == [
        "提示1",
        "请出门",
        "现在走",
    ]


@pytest.mark.parametrize("step", range(1, 27))
def test_every_sentence_end_splits(step):
    # 切分点取最早的合法句末，任意分片粒度下都按句子边界切
    text = "第一句话讲完了。第二句话也讲完了。第三句话是最后一句。"
    assert _segments(text, step) == [
        "第一句话讲完了",
        "第二句话也讲完了",
        "第三句话是最后一句",
    ]


@pytest.mark.parametrize("step", range(1, 7))
def test_colon_and_period_both_split(step):
    assert _segments("他说：好的。现在走。马上到。", step) == [
        "他说",
        "好的",
        "现在走",
        "马上到",
    ]


@pytest.mark.parametrize("step", [1, 8, 20, 50, 100])
def test_long_text_does_not_accumulate_into_one_segment(step):
    # 每个 chunk 循环切分直到切不出，任意分片粒度下都不应累积成超长段
    text = (
        "简洁明了，直接回答问题。第二条规则是：包容语音识别错误，尽量理解你的意图。"
        "第三条规则是：不要连续提问。第四条规则是：当你说再见的时候，我会礼貌地回应。"
    )
    segments = _segments(text, step)
    assert len(segments) == 7
    assert max(len(s) for s in segments) == 17
