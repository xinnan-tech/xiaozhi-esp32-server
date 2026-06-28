"""反馈记录仓储接口"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .entity import FeedbackRecord


class IFeedbackRecordRepository(ABC):
    """反馈记录仓储接口"""

    @abstractmethod
    async def get_by_id(self, record_id: str) -> Optional[FeedbackRecord]:
        ...

    @abstractmethod
    async def get_by_session_id(self, session_id: str) -> Optional[FeedbackRecord]:
        ...

    @abstractmethod
    async def save(self, record: FeedbackRecord) -> FeedbackRecord:
        ...

    @abstractmethod
    async def list_page(self, page: int = 1, page_size: int = 20,
                        store_id: Optional[str] = None,
                        employee_id: Optional[str] = None,
                        satisfaction: Optional[str] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        status: Optional[int] = None) -> dict:
        ...

    @abstractmethod
    async def count_by_store(self, store_id: str,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> int:
        ...

    @abstractmethod
    async def count_by_satisfaction(self, store_id: Optional[str] = None,
                                     start_date: Optional[str] = None,
                                     end_date: Optional[str] = None) -> dict:
        ...

    @abstractmethod
    async def get_daily_stats(self, store_id: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[dict]:
        ...
