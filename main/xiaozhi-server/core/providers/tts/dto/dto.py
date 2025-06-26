from enum import Enum
from typing import Union, Optional


class SentenceType(Enum):
    # 说话阶段
    FIRST = "FIRST"  # 首句话
    MIDDLE = "MIDDLE"  # 说话中
    LAST = "LAST"  # 最后一句


class ContentType(Enum):
    # 内容类型
    TEXT = "TEXT"  # 文本内容
    FILE = "FILE"  # 文件内容
    ACTION = "ACTION"  # 动作内容


class InterfaceType(Enum):
    # 接口类型
    DUAL_STREAM = "DUAL_STREAM"  # 双流式
    SINGLE_STREAM = "SINGLE_STREAM"  # 单流式
    NON_STREAM = "NON_STREAM"  # 非流式


class TTSMessageDTO:
    def __init__(
        self,
        sentence_id: str,
        # 说话阶段
        sentence_type: SentenceType,
        # 内容类型
        content_type: ContentType,
        # 内容详情，一般是需要转换的文本或者音频的歌词
        content_detail: Optional[str] = None,
        # 如果内容类型为文件，则需要传入文件路径
        content_file: Optional[str] = None,
    ):
        self.sentence_id = sentence_id
        self.sentence_type = sentence_type
        self.content_type = content_type
        self.content_detail = content_detail
        self.content_file = content_file
