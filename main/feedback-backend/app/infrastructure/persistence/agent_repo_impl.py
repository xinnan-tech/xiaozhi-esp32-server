"""智能体配置仓储实现"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.agent.entity import AgentConfig
from app.domain.agent.repository import IAgentConfigRepository
from app.infrastructure.persistence.models import AgentConfigModel
from app.shared.utils import generate_id


class AgentConfigRepositoryImpl(IAgentConfigRepository):
    """智能体配置仓储实现"""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _to_entity(model: AgentConfigModel) -> AgentConfig:
        return AgentConfig(
            id=model.id,
            agent_name=model.agent_name,
            agent_id=model.agent_id,
            dialogue_rounds=model.dialogue_rounds,
            questions=model.questions,
            prompts_config=model.prompts_config,
            llm_config=model.llm_config,
            review_config=model.review_config,
            status=model.status,
            create_date=model.create_date,
            update_date=model.update_date,
        )

    @staticmethod
    def _to_model(entity: AgentConfig) -> AgentConfigModel:
        return AgentConfigModel(
            id=entity.id,
            agent_name=entity.agent_name,
            agent_id=entity.agent_id,
            dialogue_rounds=entity.dialogue_rounds,
            questions=entity.questions,
            prompts_config=entity.prompts_config,
            llm_config=entity.llm_config,
            review_config=entity.review_config,
            status=entity.status,
            create_date=entity.create_date or datetime.now(),
            update_date=entity.update_date or datetime.now(),
        )

    async def get_by_id(self, config_id: str) -> Optional[AgentConfig]:
        model = self.session.query(AgentConfigModel).filter(AgentConfigModel.id == config_id).first()
        return self._to_entity(model) if model else None

    async def get_by_agent_id(self, agent_id: str) -> Optional[AgentConfig]:
        model = self.session.query(AgentConfigModel).filter(
            AgentConfigModel.agent_id == agent_id,
            AgentConfigModel.status == 1,
        ).first()
        return self._to_entity(model) if model else None

    async def list_all(self, status: Optional[int] = None) -> List[AgentConfig]:
        query = self.session.query(AgentConfigModel)
        if status is not None:
            query = query.filter(AgentConfigModel.status == status)
        models = query.order_by(AgentConfigModel.create_date.desc()).all()
        return [self._to_entity(m) for m in models]

    async def list_page(self, page: int = 1, page_size: int = 20) -> dict:
        query = self.session.query(AgentConfigModel)
        total = query.count()
        models = query.order_by(AgentConfigModel.create_date.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return {
            "list": [self._to_entity(m) for m in models],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def save(self, config: AgentConfig) -> AgentConfig:
        existing = self.session.query(AgentConfigModel).filter(AgentConfigModel.id == config.id).first()
        if existing:
            existing.agent_name = config.agent_name
            existing.agent_id = config.agent_id
            existing.dialogue_rounds = config.dialogue_rounds
            existing.questions = config.questions
            existing.prompts_config = config.prompts_config
            existing.llm_config = config.llm_config
            existing.review_config = config.review_config
            existing.status = config.status
            existing.update_date = datetime.now()
            self.session.commit()
            self.session.refresh(existing)
            return self._to_entity(existing)
        else:
            if not config.id:
                config.id = generate_id()
            model = self._to_model(config)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_entity(model)

    async def delete(self, config_id: str) -> bool:
        count = self.session.query(AgentConfigModel).filter(AgentConfigModel.id == config_id).delete()
        self.session.commit()
        return count > 0
