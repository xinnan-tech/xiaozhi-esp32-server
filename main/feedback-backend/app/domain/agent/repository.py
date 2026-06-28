"""智能体配置仓储接口"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .entity import AgentConfig


class IAgentConfigRepository(ABC):
    """智能体配置仓储接口"""

    @abstractmethod
    async def get_by_id(self, config_id: str) -> Optional[AgentConfig]:
        ...

    @abstractmethod
    async def get_by_agent_id(self, agent_id: str) -> Optional[AgentConfig]:
        ...

    @abstractmethod
    async def list_all(self, status: Optional[int] = None) -> List[AgentConfig]:
        ...

    @abstractmethod
    async def list_page(self, page: int = 1, page_size: int = 20) -> dict:
        ...

    @abstractmethod
    async def save(self, config: AgentConfig) -> AgentConfig:
        ...

    @abstractmethod
    async def delete(self, config_id: str) -> bool:
        ...
