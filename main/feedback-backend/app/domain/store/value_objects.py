"""门店值对象"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class StoreCode:
    """门店编码值对象 - 6位数字，不可变"""
    value: str

    def __post_init__(self):
        if not self.value or not self.value.isdigit() or len(self.value) != 6:
            raise ValueError(f"门店编码必须为6位数字，当前值: {self.value}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class StoreInfo:
    """门店基本信息值对象"""
    store_code: str
    store_name: str
    manager: Optional[str] = None
    shareholders: Optional[str] = None
