"""check_model_key 的行为约束。

背景：智控台下发的配置里未必带 api_key 字段，本地 LLM 场景也常把它留空。
原来的实现直接写 ``"你" in modelKey``，modelKey 为 None 时抛
``TypeError: argument of type 'NoneType' is not iterable``，
把「配置没填」这种业务错误变成了 provider 构造期的崩溃 ——
调用方想看到的那句「API key 未设置」根本来不及打印。
"""
import pytest

from core.utils.util import check_model_key


@pytest.mark.parametrize("model_key", [None, ""])
def test_missing_key_reports_error_instead_of_crashing(model_key):
    """key 没配（None / 空串）时返回提示文案，不能抛 TypeError。"""
    msg = check_model_key("LLM", model_key)
    assert msg is not None, "缺少 api_key 时应当返回提示文案"
    assert "API key 未设置" in msg


def test_placeholder_key_reports_error_with_current_value():
    """出厂占位符仍按原样提示，并带上当前值，方便用户对照改。"""
    msg = check_model_key("LLM", "你的api_key")
    assert msg is not None
    assert "API key 未设置" in msg
    assert "你的api_key" in msg


def test_real_key_passes():
    """真 key 不该被拦。"""
    assert check_model_key("LLM", "sk-abcdef123456") is None


def test_model_type_is_mentioned_in_the_message():
    """提示文案里要带上是哪个模块出的问题。"""
    msg = check_model_key("VLLM", None)
    assert "VLLM" in msg
