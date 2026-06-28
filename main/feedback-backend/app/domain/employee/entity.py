"""员工领域实体"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Employee:
    """员工实体"""
    id: str
    name: str
    number: int                     # 工号（门店内编号）
    store_id: str
    employee_type: str = "normal"   # manager/excellent/intern/normal
    status: int = 1                 # 0=禁用 1=启用
    create_date: Optional[datetime] = None
    update_date: Optional[datetime] = None

    def is_enabled(self) -> bool:
        return self.status == 1

    def is_manager(self) -> bool:
        return self.employee_type == "manager"

    def disable(self):
        self.status = 0
        self.update_date = datetime.now()

    def enable(self):
        self.status = 1
        self.update_date = datetime.now()

    @staticmethod
    def valid_employee_types() -> list:
        return ["manager", "excellent", "intern", "normal"]
