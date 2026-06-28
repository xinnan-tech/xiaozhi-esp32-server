"""员工仓储接口"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .entity import Employee


class IEmployeeRepository(ABC):
    """员工仓储接口"""

    @abstractmethod
    async def get_by_id(self, employee_id: str) -> Optional[Employee]:
        ...

    @abstractmethod
    async def list_by_store_id(self, store_id: str, status: Optional[int] = None) -> List[Employee]:
        ...

    @abstractmethod
    async def list_page(self, page: int = 1, page_size: int = 20,
                        store_id: Optional[str] = None,
                        name: Optional[str] = None,
                        status: Optional[int] = None) -> dict:
        ...

    @abstractmethod
    async def save(self, employee: Employee) -> Employee:
        ...

    @abstractmethod
    async def delete(self, employee_id: str) -> bool:
        ...

    @abstractmethod
    async def exists_by_store_and_number(self, store_id: str, number: int,
                                          exclude_id: Optional[str] = None) -> bool:
        ...
