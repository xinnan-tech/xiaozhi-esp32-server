"""智能体配置应用服务"""

from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.agent.entity import AgentConfig
from app.infrastructure.persistence.agent_repo_impl import AgentConfigRepositoryImpl
from app.shared.exceptions import AgentConfigNotFoundError, ValidationError
from app.shared.utils import generate_id


class AgentConfigService:
    """智能体配置应用服务"""

    def __init__(self, session: Session):
        self.repo = AgentConfigRepositoryImpl(session)
        self.session = session

    async def get_by_id(self, config_id: str) -> AgentConfig:
        config = await self.repo.get_by_id(config_id)
        if not config:
            raise AgentConfigNotFoundError(config_id)
        return config

    async def get_by_agent_id(self, agent_id: str) -> Optional[AgentConfig]:
        return await self.repo.get_by_agent_id(agent_id)

    async def list_page(self, page: int = 1, page_size: int = 20) -> dict:
        return await self.repo.list_page(page, page_size)

    async def create_config(self, agent_name: str, agent_id: Optional[str] = None,
                            dialogue_rounds: int = 7, questions: Optional[list] = None,
                            prompts_config: Optional[dict] = None,
                            llm_config: Optional[dict] = None,
                            review_config: Optional[dict] = None) -> AgentConfig:
        config = AgentConfig(
            id=generate_id(),
            agent_name=agent_name,
            agent_id=agent_id,
            dialogue_rounds=dialogue_rounds,
            questions=questions,
            prompts_config=prompts_config,
            llm_config=llm_config,
            review_config=review_config,
        )
        result = await self.repo.save(config)
        logger.info(f"创建智能体配置: name={agent_name}")
        return result

    async def update_config(self, config_id: str, **kwargs) -> AgentConfig:
        config = await self.repo.get_by_id(config_id)
        if not config:
            raise AgentConfigNotFoundError(config_id)

        for key, value in kwargs.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        result = await self.repo.save(config)
        logger.info(f"更新智能体配置: id={config_id}")
        return result

    async def delete_config(self, config_id: str) -> bool:
        config = await self.repo.get_by_id(config_id)
        if not config:
            raise AgentConfigNotFoundError(config_id)
        result = await self.repo.delete(config_id)
        logger.info(f"删除智能体配置: id={config_id}")
        return result
