"""门店应用服务 - 门店 CRUD 用例"""

from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

from app.domain.store.entity import Store
from app.domain.store.value_objects import StoreCode
from app.infrastructure.persistence.store_repo_impl import StoreRepositoryImpl
from app.shared.exceptions import StoreNotFoundError, ValidationError
from app.shared.utils import generate_id, is_valid_store_code


class StoreService:
    """门店应用服务"""

    def __init__(self, session: Session):
        self.repo = StoreRepositoryImpl(session)
        self.session = session

    async def get_by_store_code(self, store_code: str) -> Store:
        """根据门店编码获取门店（公开接口用）"""
        if not is_valid_store_code(store_code):
            raise ValidationError(f"门店编码格式错误: {store_code}，应为6位数字")

        store = await self.repo.get_by_store_code(store_code)
        if not store:
            raise StoreNotFoundError(store_code)
        if not store.is_enabled():
            raise StoreNotFoundError(store_code)
        return store

    async def get_by_id(self, store_id: str) -> Store:
        """根据 ID 获取门店"""
        store = await self.repo.get_by_id(store_id)
        if not store:
            raise StoreNotFoundError(store_id)
        return store

    async def list_page(self, page: int = 1, page_size: int = 20,
                        store_name: Optional[str] = None,
                        status: Optional[int] = None) -> dict:
        """分页查询门店"""
        return await self.repo.list_page(page, page_size, store_name, status)

    async def list_all(self, status: Optional[int] = None) -> list:
        """获取所有门店"""
        return await self.repo.list_all(status)

    async def create_store(self, store_code: str, store_name: str,
                           manager: Optional[str] = None,
                           shareholders: Optional[str] = None,
                           agent_id: Optional[str] = None) -> Store:
        """创建门店"""
        # 验证门店编码
        if not is_valid_store_code(store_code):
            raise ValidationError(f"门店编码格式错误: {store_code}，应为6位数字")

        # 检查编码唯一性
        if await self.repo.exists_by_store_code(store_code):
            raise ValidationError(f"门店编码已存在: {store_code}")

        store = Store(
            id=generate_id(),
            store_code=store_code,
            store_name=store_name,
            manager=manager,
            shareholders=shareholders,
            agent_id=agent_id,
        )
        result = await self.repo.save(store)
        logger.info(f"创建门店: code={store_code}, name={store_name}")
        return result

    async def update_store(self, store_id: str, **kwargs) -> Store:
        """更新门店"""
        store = await self.repo.get_by_id(store_id)
        if not store:
            raise StoreNotFoundError(store_id)

        # 如果修改了 store_code，检查唯一性
        if "store_code" in kwargs and kwargs["store_code"] != store.store_code:
            if not is_valid_store_code(kwargs["store_code"]):
                raise ValidationError(f"门店编码格式错误: {kwargs['store_code']}")
            if await self.repo.exists_by_store_code(kwargs["store_code"], exclude_id=store_id):
                raise ValidationError(f"门店编码已存在: {kwargs['store_code']}")

        for key, value in kwargs.items():
            if hasattr(store, key) and value is not None:
                setattr(store, key, value)

        result = await self.repo.save(store)
        logger.info(f"更新门店: id={store_id}")
        return result

    async def delete_store(self, store_id: str) -> bool:
        """删除门店"""
        store = await self.repo.get_by_id(store_id)
        if not store:
            raise StoreNotFoundError(store_id)
        result = await self.repo.delete(store_id)
        logger.info(f"删除门店: id={store_id}")
        return result

    async def bind_agent(self, store_id: str, agent_id: str) -> Store:
        """绑定智能体"""
        store = await self.repo.get_by_id(store_id)
        if not store:
            raise StoreNotFoundError(store_id)
        store.bind_agent(agent_id)
        result = await self.repo.save(store)
        logger.info(f"门店绑定智能体: store={store_id}, agent={agent_id}")
        return result
