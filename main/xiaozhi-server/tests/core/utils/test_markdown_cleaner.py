"""MarkdownCleaner must drop real emphasis without eating identifiers or products."""
from core.utils.tts import MarkdownCleaner


def test_identifiers_keep_their_underscores():
    assert (
        MarkdownCleaner.clean_markdown("请调用 get_current_time 函数")
        == "请调用 get_current_time 函数"
    )
    assert MarkdownCleaner.clean_markdown("a_1_b_2") == "a_1_b_2"
    assert MarkdownCleaner.clean_markdown("step_2_of_3") == "step_2_of_3"
    assert MarkdownCleaner.clean_markdown("use _em_text here") == "use _em_text here"


def test_multiplication_keeps_its_asterisks():
    assert MarkdownCleaner.clean_markdown("结果是 2*3*4 等于 24") == "结果是 2*3*4 等于 24"
    assert MarkdownCleaner.clean_markdown("a*b*c") == "a*b*c"
    assert MarkdownCleaner.clean_markdown("计算 2*3*(4+5)") == "计算 2*3*(4+5)"
    assert MarkdownCleaner.clean_markdown("计算 2*3*-4") == "计算 2*3*-4"
    assert MarkdownCleaner.clean_markdown("2*3* + 4") == "2*3* + 4"
    assert MarkdownCleaner.clean_markdown("共2*3*4元") == "共2*3*4元"
    assert MarkdownCleaner.clean_markdown("2*3*4米") == "2*3*4米"
    assert MarkdownCleaner.clean_markdown("2*3*元") == "2*3*元"
    assert MarkdownCleaner.clean_markdown("2*3*米") == "2*3*米"
    assert MarkdownCleaner.clean_markdown("3*4*（5）") == "3*4*（5）"
    assert MarkdownCleaner.clean_markdown("2*3*，") == "2*3*，"
    assert MarkdownCleaner.clean_markdown("2*3*。") == "2*3*。"
    assert MarkdownCleaner.clean_markdown("a*b*，然后") == "a*b*，然后"


def test_exponentiation_keeps_its_double_asterisks():
    assert MarkdownCleaner.clean_markdown("计算 2**3 的值") == "计算 2**3 的值"
    assert MarkdownCleaner.clean_markdown("价格 2**10 元") == "价格 2**10 元"
    assert MarkdownCleaner.clean_markdown("2**8") == "2**8"
    assert MarkdownCleaner.clean_markdown("计算 2**(3) 的值") == "计算 2**(3) 的值"
    assert MarkdownCleaner.clean_markdown("2**-3") == "2**-3"
    assert MarkdownCleaner.clean_markdown("10**-3") == "10**-3"
    assert MarkdownCleaner.clean_markdown("a**(b)") == "a**(b)"
    assert MarkdownCleaner.clean_markdown("2**[3]") == "2**[3]"
    assert MarkdownCleaner.clean_markdown("func(**kwargs)") == "func(**kwargs)"


def test_emphasis_markers_are_removed():
    assert MarkdownCleaner.clean_markdown("这是 *重点* 内容") == "这是 重点 内容"
    assert MarkdownCleaner.clean_markdown("这是 **加粗** 内容") == "这是 加粗 内容"
    assert MarkdownCleaner.clean_markdown("use _emphasis_ here") == "use emphasis here"
    assert MarkdownCleaner.clean_markdown("这是 *重要 内容* 哦") == "这是 重要 内容 哦"
    assert MarkdownCleaner.clean_markdown("use *long phrase* here") == "use long phrase here"


def test_emphasis_hugging_a_word_is_removed():
    assert MarkdownCleaner.clean_markdown("see *note*below") == "see notebelow"
    assert MarkdownCleaner.clean_markdown("这是*重点*1") == "这是重点1"
    assert MarkdownCleaner.clean_markdown("TTS*强调*") == "TTS强调"
    assert MarkdownCleaner.clean_markdown("a*重点*中文") == "a重点中文"


def test_bold_markers_are_always_removed():
    # __ 与 ** 一律按强强调剥掉
    assert MarkdownCleaner.clean_markdown("a__b__c") == "abc"
    assert MarkdownCleaner.clean_markdown("a**b**c") == "abc"
    assert MarkdownCleaner.clean_markdown("调用 __init__ 方法") == "调用 init 方法"


def test_lone_markers_are_stripped_and_do_not_become_fake_bullets():
    assert MarkdownCleaner.clean_markdown("**未闭合") == "未闭合"
    assert MarkdownCleaner.clean_markdown("**bold") == "bold"
    assert MarkdownCleaner.clean_markdown("**a *b* c") == "a b c"
    assert MarkdownCleaner.clean_markdown("*bold*text") == "boldtext"


def test_list_bullets_are_kept():
    assert MarkdownCleaner.clean_markdown("* 第一项\n* 第二项") == "- 第一项- 第二项"
    assert MarkdownCleaner.clean_markdown("+ 第一项") == "- 第一项"


def test_asterisk_inside_chinese_text_is_kept():
    assert MarkdownCleaner.clean_markdown("请按*键") == "请按*键"
    assert MarkdownCleaner.clean_markdown("中文*中文") == "中文*中文"


def test_thousands_separators_are_folded():
    assert MarkdownCleaner.clean_markdown("价格是 1_000_000 元") == "价格是 1000000 元"
    assert MarkdownCleaner.clean_markdown("价格是 1_000_000_000 元") == "价格是 1000000000 元"
    assert (
        MarkdownCleaner.clean_markdown("价格 1_000 元 和 2_000_000 元")
        == "价格 1000 元 和 2000000 元"
    )
    assert MarkdownCleaner.clean_markdown("12_000") == "12000"


def test_numbers_outside_thousands_groups_are_kept():
    # 分组必须是完整的 3 位
    assert MarkdownCleaner.clean_markdown("Python 3_10") == "Python 3_10"
    assert MarkdownCleaner.clean_markdown("版本 v2_0 beta") == "版本 v2_0 beta"
    assert MarkdownCleaner.clean_markdown("1_2_3") == "1_2_3"
    assert MarkdownCleaner.clean_markdown("甲1_0000乙") == "甲1_0000乙"
    assert MarkdownCleaner.clean_markdown("甲1_000_0000乙") == "甲1_000_0000乙"
    assert MarkdownCleaner.clean_markdown("1_000_00") == "1_000_00"
    # 千分位折叠要求整段数字独立于标识符
    assert MarkdownCleaner.clean_markdown("sensor_2_001") == "sensor_2_001"
    assert MarkdownCleaner.clean_markdown("v1_000") == "v1_000"
    assert MarkdownCleaner.clean_markdown("price_1_000") == "price_1_000"
