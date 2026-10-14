"""lang_tag_filter: SenseVoice tag parsing and CJK word-spacing cleanup."""
from core.providers.asr.utils import lang_tag_filter


def test_japanese_word_spaces_are_removed():
    result = lang_tag_filter("<|ja|><|NEUTRAL|><|Speech|><|withitn|>今日 の こと を 少し 長め に 話し て ください。")
    assert result["content"] == "今日のことを少し長めに話してください。"
    assert result["language"] == "ja"


def test_chinese_text_is_unchanged():
    result = lang_tag_filter("<|zh|><|HAPPY|><|Speech|><|withitn|>你好啊，测试测试。")
    assert result["content"] == "你好啊，测试测试。"


def test_spaces_next_to_latin_and_korean_are_kept():
    assert lang_tag_filter("<|ja|><|NEUTRAL|><|Speech|><|withitn|>OK Google と 言って")["content"] == "OK Google と言って"
    assert lang_tag_filter("<|ko|><|NEUTRAL|><|Speech|><|withitn|>안녕 하세요 반가워요")["content"] == "안녕 하세요 반가워요"
    assert lang_tag_filter("<|en|><|NEUTRAL|><|Speech|><|withitn|>Hello world.")["content"] == "Hello world."


def test_plain_text_without_tags():
    assert lang_tag_filter("plain text") == {"content": "plain text"}
