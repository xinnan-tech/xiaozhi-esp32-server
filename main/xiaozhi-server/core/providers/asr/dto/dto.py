from enum import Enum
from typing import Union, Optional


class InterfaceType(Enum):
    # 接口类型
    STREAM = "STREAM"  # 流式接口
    NON_STREAM = "NON_STREAM"  # 非流式接口
    LOCAL = "LOCAL"  # 本地服务
