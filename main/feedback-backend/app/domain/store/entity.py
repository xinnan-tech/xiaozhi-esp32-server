"""门店领域实体"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Store:
    """门店实体 - DDD 领域模型，纯 Python，不依赖任何框架"""
    id: str
    store_code: str       # 6位门店编码，客户扫码用
    store_name: str
    manager: Optional[str] = None
    shareholders: Optional[str] = None  # 逗号分隔
    agent_id: Optional[str] = None      # 绑定的智能体 ID
    status: int = 1                     # 0=禁用 1=启用
    create_date: Optional[datetime] = None
    update_date: Optional[datetime] = None

    def is_enabled(self) -> bool:
        return self.status == 1

    def disable(self):
        self.status = 0
        self.update_date = datetime.now()

    def enable(self):
        self.status = 1
        self.update_date = datetime.now()

    def bind_agent(self, agent_id: str):
        self.agent_id = agent_id
        self.update_date = datetime.now()

    def unbind_agent(self):
        self.agent_id = None
        self.update_date = datetime.now()
