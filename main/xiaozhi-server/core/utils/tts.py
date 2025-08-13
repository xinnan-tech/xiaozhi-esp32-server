import os
import re
import sys
from config.logger import setup_logging
import importlib

logger = setup_logging()


def create_instance(class_name, *args, **kwargs):
    # Create TTS instance
    if os.path.exists(os.path.join('core', 'providers', 'tts', f'{class_name}.py')):
        lib_name = f'core.providers.tts.{class_name}'
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(f'{lib_name}')
        return sys.modules[lib_name].TTSProvider(*args, **kwargs)

    raise ValueError(
        f"Unsupported TTS type: {class_name}, please check if the type configuration is correct")


class MarkdownCleaner:
    """
    Encapsulate Markdown cleaning logic: directly use MarkdownCleaner.clean_markdown(text)
    """
    # Formula characters
    NORMAL_FORMULA_CHARS = re.compile(r'[a-zA-Z\\^_{}\+\-\(\)\[\]=]')

    @staticmethod
    def _replace_inline_dollar(m: re.Match) -> str:
        """
        When capturing complete "$...$":
        - If there are typical formula characters inside => remove $ on both sides
        - Otherwise (pure numbers/currency etc) => keep "$...$"
        """
        content = m.group(1)
        if MarkdownCleaner.NORMAL_FORMULA_CHARS.search(content):
            return content
        else:
            return m.group(0)

    @staticmethod
    def _replace_table_block(match: re.Match) -> str:
        """
        When matching an entire table block, this function is called back.
        """
        block_text = match.group('table_block')
        lines = block_text.strip('\n').split('\n')
        parsed_table = []

        for line in lines:
            line_stripped = line.strip()
            if re.match(r'^\|\s*[-:]+\s*(\|\s*[-:]+\s*)+\|?$', line_stripped):
                continue

            columns = [col.strip()
                       for col in line_stripped.split('|') if col.strip() != '']
            if columns:
                parsed_table.append(columns)

        if not parsed_table:
            return ""

        headers = parsed_table[0]
        data_rows = parsed_table[1:] if len(parsed_table) > 1 else []
        lines_for_tts = []

        if len(parsed_table) == 1:
            # Only one row
            only_line_str = ", ".join(parsed_table[0])
            lines_for_tts.append(f"Single row table: {only_line_str}")
        else:
            lines_for_tts.append(f"Headers are: {', '.join(headers)}")
            for i, row in enumerate(data_rows, start=1):
                row_str_list = []
                for col_index, cell_val in enumerate(row):
                    if col_index < len(headers):
                        row_str_list.append(
                            f"{headers[col_index]} = {cell_val}")
                    else:
                        row_str_list.append(cell_val)
                lines_for_tts.append(f"Row {i}: {', '.join(row_str_list)}")

        return "\n".join(lines_for_tts) + "\n"

    # Pre-compile all regular expressions (ordered by execution frequency)
    # Here we need to put replace_xxx static methods at the front to reference them correctly in the list.
    REGEXES = [
        (re.compile(r'``````', re.DOTALL), ''),  # Code blocks
        (re.compile(r'^#+\s*', re.MULTILINE), ''),  # Headers
        (re.compile(r'(\*\*|__)(.*?)\1'), r'\2'),  # Bold
        (re.compile(r'(\*|_)(?=\S)(.*?)(?<=\S)\1'), r'\2'),  # Italic
        (re.compile(r'!\[.*?\]\(.*?\)'), ''),  # Images
        (re.compile(r'\[(.*?)\]\(.*?\)'), r'\1'),  # Links
        (re.compile(r'^\s*>+\s*', re.MULTILINE), ''),  # Quotes
        (
            re.compile(
                r'(?P<table_block>(?:^[^\n]*\|[^\n]*\n)+)', re.MULTILINE),
            _replace_table_block
        ),
        (re.compile(r'^\s*[*+-]\s*', re.MULTILINE), '- '),  # Lists
        (re.compile(r'\$\$.*?\$\$', re.DOTALL), ''),  # Block formulas
        (
            re.compile(r'(?<!\$)\$([^$\n]+?)\$(?!\$)'),
            _replace_inline_dollar
        ),  # Inline formulas
    ]

    @staticmethod
    def clean_markdown(text: str) -> str:
        """
        Main entry method: execute all regex in sequence, remove or replace Markdown elements
        """
        for regex, replacement in MarkdownCleaner.REGEXES:
            text = regex.sub(replacement, text)
        return text.strip()
