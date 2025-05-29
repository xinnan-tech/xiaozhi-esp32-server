def get_string_no_punctuation_or_emoji(s):
    """去除字符串首尾的空格、标点符号和表情符号"""
    chars = list(s)
    # 处理开头的字符
    start = 0
    while start < len(chars) and is_punctuation_or_emoji(chars[start]):
        start += 1
    # 处理结尾的字符
    end = len(chars) - 1
    while end >= start and is_punctuation_or_emoji(chars[end]):
        end -= 1
    return ''.join(chars[start:end + 1])

def is_punctuation_or_emoji(char):
    """检查字符是否为空格、指定标点或表情符号"""
    # 定义需要去除的中英文标点（包括全角/半角）
    punctuation_set = {
        '，', ',',  # 中文逗号 + 英文逗号
        '。', '.',  # 中文句号 + 英文句号
        '！', '!',  # 中文感叹号 + 英文感叹号
        '-', '－',  # 英文连字符 + 中文全角横线
        '、'  # 中文顿号
    }
    if char.isspace() or char in punctuation_set:
        return True
    # 检查表情符号（保留原有逻辑）
    code_point = ord(char)
    emoji_ranges = [
        (0x1F600, 0x1F64F), (0x1F300, 0x1F5FF),
        (0x1F680, 0x1F6FF), (0x1F900, 0x1F9FF),
        (0x1FA70, 0x1FAFF), (0x2600, 0x26FF),
        (0x2700, 0x27BF)
    ]
    return any(start <= code_point <= end for start, end in emoji_ranges)