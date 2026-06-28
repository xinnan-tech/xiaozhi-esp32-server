"""共享工具函数"""

import re
import uuid
from datetime import datetime
from typing import Any


def generate_id() -> str:
    """生成 64 位字符串 ID（与 Java ASSIGN_ID 策略兼容）"""
    return str(uuid.uuid4()).replace("-", "")[:64]


def now() -> datetime:
    """获取当前时间"""
    return datetime.now()


def is_valid_store_code(code: str) -> bool:
    """验证门店编码：6 位数字"""
    return bool(re.match(r"^\d{6}$", code))


def sanitize_text(text: str) -> str:
    """清理文本：去除首尾空白，压缩连续空白"""
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def parse_satisfaction(value: str) -> dict:
    """解析满意度值，返回标准化的满意度信息"""
    mapping = {
        "very_satisfied": {"level": "very_satisfied", "text": "非常满意", "score": 4},
        "satisfied": {"level": "satisfied", "text": "满意", "score": 3},
        "unsatisfied": {"level": "unsatisfied", "text": "不满意", "score": 2},
        "very_bad": {"level": "very_bad", "text": "很差", "score": 1},
    }
    return mapping.get(value, {"level": "unknown", "text": "未知", "score": 0})


def should_generate_review(satisfaction: str) -> bool:
    """是否应生成点评（仅满意时生成）"""
    return satisfaction in ("very_satisfied", "satisfied")


def load_prompt_template(file_path: str) -> str:
    """加载提示词模板文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def render_prompt(template: str, **kwargs) -> str:
    """渲染提示词模板，支持 {{变量名}} 语法"""
    result = template
    for key, value in kwargs.items():
        result = result.replace("{{" + key + "}}", str(value))
    return result


def paginate(items: list, page: int = 1, page_size: int = 20) -> dict:
    """通用分页"""
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "list": items[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }
