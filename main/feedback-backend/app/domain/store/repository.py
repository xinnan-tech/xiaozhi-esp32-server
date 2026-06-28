"""门店仓储接口 - 领域层只定义接口，实现在基础设施层"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .entity import Store


class IStoreRepository(ABC):
    """门店仓储接口"""

    @abstractmethod
    async def get_by_id(self, store_id: str) -> Optional[Store]:
        """根据 ID 获取门店"""
        ...

    @abstractmethod
    async def get_by_store_code(self, store_code: str) -> Optional[Store]:
        """根据门店编码获取门店"""
        ...

    @abstractmethod
    async def list_all(self, status: Optional[int] = None) -> List[Store]:
        """获取门店列表"""
        ...

    @abstractmethod
    async def list_page(self, page: int = 1, page_size: int = 20,
                        store_name: Optional[str] = None,
                        status: Optional[int] = None) -> dict:
        """分页获取门店列表"""
        ...

    @abstractmethod
    async def save(self, store: Store) -> Store:
        """保存门店（新增或更新）"""
        ...

    @abstractmethod
    async def delete(self, store_id: str) -> bool:
        """删除门店"""
        ...

    @abstractmethod
    async def exists_by_store_code(self, store_code: str, exclude_id: Optional[str] = None) -> bool:
        """门店编码是否已存在"""
        ...
