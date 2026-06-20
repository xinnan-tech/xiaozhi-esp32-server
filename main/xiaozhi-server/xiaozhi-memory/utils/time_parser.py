"""
时间解析工具
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import re

try:
    from dateutil.relativedelta import relativedelta
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


class TimeParser:
    """时间解析器"""

    # 相对时间正则表达式
    PATTERNS = {
        '今天': r'今天',
        '明天': r'明天',
        '后天': r'后天',
        '后天2': r'(\d+)天[后之]',
        '昨天': r'昨天',
        '前天': r'前天',
        '前天2': r'(\d+)天[前之]',
        '下周': r'下个?周|下星期',
        '上周': r'上个?周|上星期',
        '这周': r'这周|本周|这个星期',
        '下周几': r'下个?(周|星期)([一二三四五六七天日])',
        '个月': r'(\d+)个?月[后之]',
        '个月前': r'(\d+)个?月前',
        '年后': r'(\d+)年[后之]',
        '年前': r'(\d+)年前',
    }

    WEEKDAYS = {
        '一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6,
        '1': 0, '2': 1, '3': 2, '4': 3, '5': 4, '6': 5, '7': 6
    }

    @classmethod
    def parse(cls, text: str, reference_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        解析相对时间表达式

        Args:
            text: 时间文本，如"两天后"、"明天下午3点"
            reference_date: 参考日期，默认为今天

        Returns:
            {
                "absolute": "2025-05-22T14:00:00",  # 绝对时间
                "relative": "两天后",  # 原始相对时间描述
                "confidence": 1.0  # 置信度
            }
        """
        if reference_date is None:
            reference_date = datetime.now()

        result = {
            "absolute": None,
            "relative": text.strip(),
            "confidence": 0.0
        }

        # 尝试各种模式
        absolute_time = None

        # 今天
        if re.search(cls.PATTERNS['今天'], text):
            absolute_time = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
            result['confidence'] = 1.0

        # 明天
        elif re.search(cls.PATTERNS['明天'], text):
            absolute_time = reference_date + timedelta(days=1)
            absolute_time = absolute_time.replace(hour=0, minute=0, second=0, microsecond=0)
            result['confidence'] = 1.0

        # 后天
        elif re.search(cls.PATTERNS['后天'], text):
            absolute_time = reference_date + timedelta(days=2)
            absolute_time = absolute_time.replace(hour=0, minute=0, second=0, microsecond=0)
            result['confidence'] = 1.0

        # N天后
        elif m := re.search(cls.PATTERNS['后天2'], text):
            days = int(m.group(1))
            absolute_time = reference_date + timedelta(days=days)
            absolute_time = absolute_time.replace(hour=0, minute=0, second=0, microsecond=0)
            result['confidence'] = 0.9

        # 昨天
        elif re.search(cls.PATTERNS['昨天'], text):
            absolute_time = reference_date - timedelta(days=1)
            absolute_time = absolute_time.replace(hour=0, minute=0, second=0, microsecond=0)
            result['confidence'] = 1.0

        # 前天
        elif re.search(cls.PATTERNS['前天'], text):
            absolute_time = reference_date - timedelta(days=2)
            absolute_time = absolute_time.replace(hour=0, minute=0, second=0, microsecond=0)
            result['confidence'] = 1.0

        # N天前
        elif m := re.search(cls.PATTERNS['前天2'], text):
            days = int(m.group(1))
            absolute_time = reference_date - timedelta(days=days)
            absolute_time = absolute_time.replace(hour=0, minute=0, second=0, microsecond=0)
            result['confidence'] = 0.9

        # 下周
        elif re.search(cls.PATTERNS['下周'], text):
            # 下周一
            days_to_monday = (7 - reference_date.weekday()) % 7
            if days_to_monday == 0:
                days_to_monday = 7
            absolute_time = reference_date + timedelta(days=days_to_monday)
            absolute_time = absolute_time.replace(hour=0, minute=0, second=0, microsecond=0)
            result['confidence'] = 0.8

        # 下周X
        elif m := re.search(cls.PATTERNS['下周几'], text):
            weekday = cls.WEEKDAYS.get(m.group(2), 0)
            days_ahead = (weekday - reference_date.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            absolute_time = reference_date + timedelta(days=days_ahead)
            absolute_time = absolute_time.replace(hour=0, minute=0, second=0, microsecond=0)
            result['confidence'] = 0.9

        # N个月后
        elif m := re.search(cls.PATTERNS['个月'], text):
            months = int(m.group(1))
            # 使用 relativedelta 进行精确的月份计算
            if HAS_DATEUTIL:
                absolute_time = reference_date + relativedelta(months=months)
            else:
                # 回退方案：手动计算月份（考虑不同月份的天数差异）
                year = reference_date.year
                month = reference_date.month + months
                while month > 12:
                    month -= 12
                    year += 1
                # 保持日期不变，如果目标月份没有该日期，则使用该月最后一天
                day = min(reference_date.day, [31, 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
                absolute_time = reference_date.replace(year=year, month=month, day=day)
            absolute_time = absolute_time.replace(hour=0, minute=0, second=0, microsecond=0)
            result['confidence'] = 0.7

        # N个月前
        elif m := re.search(cls.PATTERNS['个月前'], text):
            months = int(m.group(1))
            # 使用 relativedelta 进行精确的月份计算
            if HAS_DATEUTIL:
                absolute_time = reference_date - relativedelta(months=months)
            else:
                # 回退方案：手动计算月份
                year = reference_date.year
                month = reference_date.month - months
                while month <= 0:
                    month += 12
                    year -= 1
                # 保持日期不变，如果目标月份没有该日期，则使用该月最后一天
                day = min(reference_date.day, [31, 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
                absolute_time = reference_date.replace(year=year, month=month, day=day)
            absolute_time = absolute_time.replace(hour=0, minute=0, second=0, microsecond=0)
            result['confidence'] = 0.7

        # 尝试解析具体时间（如"下午3点"）
        if absolute_time:
            # 检查是否包含具体时间
            time_match = re.search(r'([上下]午)?([012]?[0-9]):([0-5][0-9])', text)
            if time_match:
                hour = int(time_match.group(2))
                minute = int(time_match.group(3))
                if time_match.group(1) == '下午' and hour < 12:
                    hour += 12
                absolute_time = absolute_time.replace(hour=hour, minute=minute)

        if absolute_time:
            result['absolute'] = absolute_time.isoformat()

        return result

    @classmethod
    def extract_all_time_references(cls, text: str, reference_date: Optional[datetime] = None) -> list:
        """
        提取文本中所有时间引用

        Args:
            text: 输入文本
            reference_date: 参考日期

        Returns:
            时间引用列表
        """
        results = []

        # 按句子分割
        sentences = re.split(r'[。！？；;]', text)

        for sentence in sentences:
            if not sentence.strip():
                continue

            parsed = cls.parse(sentence.strip(), reference_date)
            if parsed['absolute']:
                results.append(parsed)

        return results
