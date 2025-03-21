import os
import re
import sys
from config.logger import setup_logging
import importlib

logger = setup_logging()


def create_instance(class_name, *args, **kwargs):
    # 创建TTS实例
    if os.path.exists(os.path.join('core', 'providers', 'tts', f'{class_name}.py')):
        lib_name = f'core.providers.tts.{class_name}'
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(f'{lib_name}')
        return sys.modules[lib_name].TTSProvider(*args, **kwargs)

    raise ValueError(f"不支持的TTS类型: {class_name}，请检查该配置的type是否设置正确")


class MarkdownCleaner:
    """
    封装 Markdown 清理逻辑：直接用 MarkdownCleaner.clean_markdown(text) 即可
    """
    # 公式字符
    NORMAL_FORMULA_CHARS = re.compile(r'[a-zA-Z\\^_{}\+\-\(\)\[\]=]')

    @staticmethod
    def _replace_inline_dollar(m: re.Match) -> str:
        """
        只要捕获到完整的 "$...$":
          - 如果内部有典型公式字符 => 去掉两侧 $
          - 否则 (纯数字/货币等) => 保留 "$...$"
        """
        content = m.group(1)
        if MarkdownCleaner.NORMAL_FORMULA_CHARS.search(content):
            return content
        else:
            return m.group(0)

    @staticmethod
    def _replace_table_block(match: re.Match) -> str:
        """
        当匹配到一个整段表格块时，回调该函数。
        """
        block_text = match.group('table_block')
        lines = block_text.strip('\n').split('\n')

        parsed_table = []
        for line in lines:
            line_stripped = line.strip()
            if re.match(r'^\|\s*[-:]+\s*(\|\s*[-:]+\s*)+\|?$', line_stripped):
                continue
            columns = [col.strip() for col in line_stripped.split('|') if col.strip() != '']
            if columns:
                parsed_table.append(columns)

        if not parsed_table:
            return ""

        headers = parsed_table[0]
        data_rows = parsed_table[1:] if len(parsed_table) > 1 else []

        lines_for_tts = []
        if len(parsed_table) == 1:
            # 只有一行
            only_line_str = ", ".join(parsed_table[0])
            lines_for_tts.append(f"单行表格：{only_line_str}")
        else:
            lines_for_tts.append(f"表头是：{', '.join(headers)}")
            for i, row in enumerate(data_rows, start=1):
                row_str_list = []
                for col_index, cell_val in enumerate(row):
                    if col_index < len(headers):
                        row_str_list.append(f"{headers[col_index]} = {cell_val}")
                    else:
                        row_str_list.append(cell_val)
                lines_for_tts.append(f"第 {i} 行：{', '.join(row_str_list)}")

        return "\n".join(lines_for_tts) + "\n"

    # 预编译所有正则表达式（按执行频率排序）
    # 这里要把 replace_xxx 的静态方法放在最前定义，以便在列表里能正确引用它们。
    REGEXES = [
        (re.compile(r'```.*?```', re.DOTALL), ''),  # 代码块
        (re.compile(r'^#+\s*', re.MULTILINE), ''),  # 标题
        (re.compile(r'(\*\*|__)(.*?)\1'), r'\2'),  # 粗体
        (re.compile(r'(\*|_)(?=\S)(.*?)(?<=\S)\1'), r'\2'),  # 斜体
        (re.compile(r'!\[.*?\]\(.*?\)'), ''),  # 图片
        (re.compile(r'\[(.*?)\]\(.*?\)'), r'\1'),  # 链接
        (re.compile(r'^\s*>+\s*', re.MULTILINE), ''),  # 引用
        (
            re.compile(r'(?P<table_block>(?:^[^\n]*\|[^\n]*\n)+)', re.MULTILINE),
            _replace_table_block
        ),
        (re.compile(r'^\s*[*+-]\s*', re.MULTILINE), '- '),  # 列表
        (re.compile(r'\$\$.*?\$\$', re.DOTALL), ''),  # 块级公式
        (
            re.compile(r'(?<![A-Za-z0-9])\$([^\n$]+)\$(?![A-Za-z0-9])'),
            _replace_inline_dollar
        ),
        (re.compile(r'\n{2,}'), '\n'),  # 多余空行
    ]

    @staticmethod
    def clean_markdown(text: str) -> str:
        """
        主入口方法：依序执行所有正则，移除或替换 Markdown 元素
        """
        for regex, replacement in MarkdownCleaner.REGEXES:
            text = regex.sub(replacement, text)
        return text.strip()