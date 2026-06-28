"""员工值对象"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EmployeeType:
    """员工类型值对象"""
    value: str

    VALID_TYPES = {"manager", "excellent", "intern", "normal"}

    def __post_init__(self):
        if self.value not in self.VALID_TYPES:
            raise ValueError(f"无效的员工类型: {self.value}，有效值: {self.VALID_TYPES}")

    def __str__(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        names = {
            "manager": "店长",
            "excellent": "优秀员工",
            "intern": "实习生",
            "normal": "普通员工",
        }
        return names.get(self.value, self.value)
