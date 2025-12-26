import re
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


def lang_tag_filter(text):
    """
    过滤函数：只保留语言标签，移除其他所有标签
    
    用于FunASR识别结果的处理，保留语言标签（如<|zh|>、<|en|>等），
    但移除其他所有格式的标签（如时间戳、情感标签等）
    
    Args:
        text: ASR识别的原始文本，可能包含多种标签
        
    Returns:
        str: 处理后的文本，只保留语言标签（如果存在）
        
    Examples:
        >>> lang_tag_filter("<|zh|><|emotion:happy|>你好")
        '<|zh|>你好'
        >>> lang_tag_filter("<|en|>hello world")
        '<|en|>hello world'
    """
    # 定义语言标签模式
    lang_pattern = r"<\|(zh|en|yue|ja|ko|nospeech)\|>"
    lang_tags = re.findall(lang_pattern, text)

    # 移除所有 < | ... | > 格式的标签
    clean_text = re.sub(r"<\|.*?\|>", "", text)

    # 在开头添加语言标签（如果存在）
    if lang_tags:
        if len(lang_tags) > 1:
            logger.bind(tag=TAG).warning(
                f"检测到多个语言标签: {lang_tags}，仅使用第一个: {lang_tags[0]}"
            )
        clean_text = f"<|{lang_tags[0]}|>{clean_text}"

    return clean_text.strip()

