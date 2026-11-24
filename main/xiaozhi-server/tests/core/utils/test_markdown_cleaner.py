"""MarkdownCleaner must drop real emphasis without eating identifiers or products."""
from core.utils.tts import MarkdownCleaner


def test_snake_case_is_not_read_as_italic():
    assert (
        MarkdownCleaner.clean_markdown("请调用 get_current_time 函数")
        == "请调用 get_current_time 函数"
    )
    assert MarkdownCleaner.clean_markdown("a_b_c 结束") == "a_b_c 结束"


def test_multiplication_is_not_read_as_italic():
    assert MarkdownCleaner.clean_markdown("结果是 2*3*4 等于 24") == "结果是 2*3*4 等于 24"


def test_numeric_underscores_are_still_removed():
    # 数字里的下划线不是标识符，读出来应是连续数字
    assert MarkdownCleaner.clean_markdown("价格是 1_000_000 元") == "价格是 1000000 元"


def test_emphasis_markers_are_still_removed():
    assert MarkdownCleaner.clean_markdown("这是 *重点* 内容") == "这是 重点 内容"
    assert MarkdownCleaner.clean_markdown("这是 **加粗** 内容") == "这是 加粗 内容"
    assert MarkdownCleaner.clean_markdown("use _emphasis_ here") == "use emphasis here"
