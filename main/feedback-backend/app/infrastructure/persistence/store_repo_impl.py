"""门店仓储实现 - ORM Model <-> Domain Entity 转换"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.domain.store.entity import Store
from app.domain.store.repository import IStoreRepository
from app.infrastructure.persistence.models import StoreModel
from app.shared.utils import generate_id


class StoreRepositoryImpl(IStoreRepository):
    """门店仓储实现"""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def _to_entity(model: StoreModel) -> Store:
        """ORM Model -> Domain Entity"""
        return Store(
            id=model.id,
            store_code=model.store_code,
            store_name=model.store_name,
            manager=model.manager,
            shareholders=model.shareholders,
            agent_id=model.agent_id,
            status=model.status,
            create_date=model.create_date,
            update_date=model.update_date,
        )

    @staticmethod
    def _to_model(entity: Store) -> StoreModel:
        """Domain Entity -> ORM Model"""
        return StoreModel(
            id=entity.id,
            store_code=entity.store_code,
            store_name=entity.store_name,
            manager=entity.manager,
            shareholders=entity.shareholders,
            agent_id=entity.agent_id,
            status=entity.status,
            create_date=entity.create_date or datetime.now(),
            update_date=entity.update_date or datetime.now(),
        )

    async def get_by_id(self, store_id: str) -> Optional[Store]:
        model = self.session.query(StoreModel).filter(StoreModel.id == store_id).first()
        return self._to_entity(model) if model else None

    async def get_by_store_code(self, store_code: str) -> Optional[Store]:
        model = self.session.query(StoreModel).filter(
            StoreModel.store_code == store_code
        ).first()
        return self._to_entity(model) if model else None

    async def list_all(self, status: Optional[int] = None) -> List[Store]:
        query = self.session.query(StoreModel)
        if status is not None:
            query = query.filter(StoreModel.status == status)
        models = query.order_by(StoreModel.create_date.desc()).all()
        return [self._to_entity(m) for m in models]

    async def list_page(self, page: int = 1, page_size: int = 20,
                        store_name: Optional[str] = None,
                        status: Optional[int] = None) -> dict:
        query = self.session.query(StoreModel)
        if store_name:
            query = query.filter(StoreModel.store_name.like(f"%{store_name}%"))
        if status is not None:
            query = query.filter(StoreModel.status == status)

        total = query.count()
        models = query.order_by(StoreModel.create_date.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return {
            "list": [self._to_entity(m) for m in models],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def save(self, store: Store) -> Store:
        existing = self.session.query(StoreModel).filter(StoreModel.id == store.id).first()
        if existing:
            existing.store_code = store.store_code
            existing.store_name = store.store_name
            existing.manager = store.manager
            existing.shareholders = store.shareholders
            existing.agent_id = store.agent_id
            existing.status = store.status
            existing.update_date = datetime.now()
            self.session.commit()
            self.session.refresh(existing)
            return self._to_entity(existing)
        else:
            if not store.id:
                store.id = generate_id()
            model = self._to_model(store)
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)
            return self._to_entity(model)

    async def delete(self, store_id: str) -> bool:
        count = self.session.query(StoreModel).filter(StoreModel.id == store_id).delete()
        self.session.commit()
        return count > 0

    async def exists_by_store_code(self, store_code: str, exclude_id: Optional[str] = None) -> bool:
        query = self.session.query(StoreModel).filter(StoreModel.store_code == store_code)
        if exclude_id:
            query = query.filter(StoreModel.id != exclude_id)
        return query.first() is not None
