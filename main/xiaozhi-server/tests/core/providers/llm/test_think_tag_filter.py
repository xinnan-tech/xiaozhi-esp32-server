"""iter_answer_text：把推理模型的思考内容剥掉，只留正文。

背景：DeepSeek / Qwen3 这类推理模型会在正文前面塞一段
<think>...</think> 的推理过程。原来的实现先按 <think> 截断 content，
同一个 chunk 里带着 </think> 时，截断后就再也匹配不到闭标签，
「正在思考」这个状态永远退不出去 —— 整段回复连同后面的 chunk 全被
丢掉，设备一句话都不说。
"""


def _answer_text(contents):
    """跑一遍 iter_answer_text，返回它吐出来的文本列表。

    导入放在函数里：core.providers.llm.openai.openai 在 import 期就要
    config/settings.py 里的 data/.config.yaml，缺了会直接抛
    FileNotFoundError，把整个收集阶段带崩。
    """
    from core.providers.llm.openai.openai import iter_answer_text

    return list(iter_answer_text(contents))


def test_plain_text_passes_through():
    assert _answer_text(["你好", "，", "在吗"]) == ["你好", "，", "在吗"]


def test_think_block_in_one_chunk():
    """服务端一次性吐出整段思考块时，正文必须还在。"""
    assert _answer_text(["<think>推理过程</think>你好"]) == ["你好"]


def test_think_block_split_across_chunks():
    """思考块被拆成多个 chunk 时，只有推理内容被丢掉。"""
    assert _answer_text(["<think>", "推理", "过程", "</think>", "你好"]) == ["你好"]


def test_text_before_think_is_kept():
    assert _answer_text(["前缀<think>推理</think>正文"]) == ["前缀", "正文"]


def test_closing_tag_without_opening_tag():
    """只有闭标签时，从闭标签之后开始算正文。"""
    assert _answer_text(["正文</think>尾巴"]) == ["尾巴"]


def test_chunks_after_think_are_kept():
    """思考块结束后，后续 chunk 必须继续输出，不能整段丢。"""
    assert _answer_text(["<think>abc</think>", "第一句", "第二句"]) == ["第一句", "第二句"]


def test_empty_chunks_are_ignored():
    assert _answer_text(["", "你好", ""]) == ["你好"]
