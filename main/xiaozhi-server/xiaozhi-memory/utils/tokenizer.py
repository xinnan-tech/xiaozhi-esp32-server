"""
中文分词工具
"""
from typing import List
import re


class Tokenizer:
    """分词器基类"""

    def tokenize(self, text: str) -> List[str]:
        """分词"""
        pass


class JiebaTokenizer(Tokenizer):
    """jieba分词器"""

    def __init__(self):
        try:
            import jieba
            self.jieba = jieba
            self.available = True
        except ImportError:
            self.available = False

    def tokenize(self, text: str) -> List[str]:
        """使用jieba分词"""
        if not self.available:
            # 降级到简单分词
            return SimpleTokenizer().tokenize(text)
        return list(self.jieba.lcut(text))


class SimpleTokenizer(Tokenizer):
    """简单分词器（按字符和空格）"""

    def tokenize(self, text: str) -> List[str]:
        """简单分词：按空格分割，并对中文按字符分割"""
        # 先按空格分割
        parts = text.split()
        tokens = []

        for part in parts:
            # 检查是否包含中文
            if re.search(r'[一-鿿]', part):
                # 中文按字符分割
                tokens.extend(list(part))
            else:
                # 英文按空格分割
                tokens.append(part)

        return tokens


class Unicode61Tokenizer(Tokenizer):
    """SQLite FTS5 unicode61分词器模拟"""

    def tokenize(self, text: str) -> List[str]:
        """类似unicode61的分词：按空格和标点分割"""
        # 按非字母数字字符分割
        tokens = re.findall(r'\w+', text)
        return tokens


# 默认分词器
_default_tokenizer = None


def get_tokenizer() -> Tokenizer:
    """获取默认分词器"""
    global _default_tokenizer
    if _default_tokenizer is None:
        # 优先使用jieba
        _default_tokenizer = JiebaTokenizer()
    return _default_tokenizer


def tokenize(text: str) -> List[str]:
    """分词便捷函数"""
    return get_tokenizer().tokenize(text)


def tokenize_to_string(text: str) -> str:
    """分词并返回字符串（用于FTS5）"""
    tokens = tokenize(text)
    return " ".join(tokens)
