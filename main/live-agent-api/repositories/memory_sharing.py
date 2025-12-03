from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, TIMESTAMP, ForeignKey, Index, select, delete
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database import Base, utc_now


# ==================== ORM Models ====================

class MemorySharingModel(Base):
    """记忆共享配置表"""
    __tablename__ = "memory_sharing"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(50), nullable=False)
    share_type: Mapped[str] = mapped_column(String(20), nullable=False)  # none, specific, all
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=utc_now, 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=utc_now, 
        onupdate=utc_now, 
        nullable=False
    )

    __table_args__ = (
        Index('idx_memory_sharing_user_id', 'user_id'),
        Index('idx_memory_sharing_agent_id', 'agent_id'),
    )


class MemorySharingTargetModel(Base):
    """记忆共享目标表（specific 类型使用）"""
    __tablename__ = "memory_sharing_targets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sharing_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("memory_sharing.id", ondelete="CASCADE"),
        nullable=False
    )
    target_agent_id: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        default=utc_now, 
        nullable=False
    )

    __table_args__ = (
        Index('idx_memory_sharing_targets_sharing_id', 'sharing_id'),
        Index('idx_memory_sharing_targets_target_agent_id', 'target_agent_id'),
    )


# ==================== Repository ====================

class MemorySharingRepository:
    """记忆共享配置 Repository"""

    @staticmethod
    async def get_config(
        db: AsyncSession,
        user_id: str,
        agent_id: str
    ) -> Optional[MemorySharingModel]:
        """获取共享配置"""
        result = await db.execute(
            select(MemorySharingModel).where(
                MemorySharingModel.user_id == user_id,
                MemorySharingModel.agent_id == agent_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_shared_with(
        db: AsyncSession,
        sharing_id: int
    ) -> List[str]:
        """获取共享目标 agent 列表"""
        result = await db.execute(
            select(MemorySharingTargetModel.target_agent_id).where(
                MemorySharingTargetModel.sharing_id == sharing_id
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def upsert_config(
        db: AsyncSession,
        user_id: str,
        agent_id: str,
        share_type: str,
        shared_with: Optional[List[str]] = None
    ) -> MemorySharingModel:
        """创建或更新共享配置"""
        # 查找现有配置
        config = await MemorySharingRepository.get_config(db, user_id, agent_id)
        
        if config:
            # 更新
            config.share_type = share_type
        else:
            # 创建
            config = MemorySharingModel(
                user_id=user_id,
                agent_id=agent_id,
                share_type=share_type
            )
            db.add(config)
        
        await db.flush()  # 获取 config.id
        
        # 更新共享目标（先删除旧的，再添加新的）
        await db.execute(
            delete(MemorySharingTargetModel).where(
                MemorySharingTargetModel.sharing_id == config.id
            )
        )
        
        if share_type == "specific" and shared_with:
            for target_agent_id in shared_with:
                target = MemorySharingTargetModel(
                    sharing_id=config.id,
                    target_agent_id=target_agent_id
                )
                db.add(target)
        
        await db.commit()
        await db.refresh(config)
        return config

    @staticmethod
    async def get_agents_sharing_to(
        db: AsyncSession,
        user_id: str,
        target_agent_id: str
    ) -> List[str]:
        """
        获取共享记忆给指定 agent 的所有源 agent 列表
        
        条件：
        1. share_type = 'all' 的所有 agent（同一 user 下）
        2. share_type = 'specific' 且 target_agent_id 在 shared_with 列表中
        """
        # 1. share_type = 'all' 的 agents
        all_sharing_result = await db.execute(
            select(MemorySharingModel.agent_id).where(
                MemorySharingModel.user_id == user_id,
                MemorySharingModel.share_type == "all",
                MemorySharingModel.agent_id != target_agent_id  # 排除自己
            )
        )
        all_sharing_agents = list(all_sharing_result.scalars().all())
        
        # 2. share_type = 'specific' 且包含 target_agent_id
        specific_sharing_result = await db.execute(
            select(MemorySharingModel.agent_id)
            .join(
                MemorySharingTargetModel,
                MemorySharingModel.id == MemorySharingTargetModel.sharing_id
            )
            .where(
                MemorySharingModel.user_id == user_id,
                MemorySharingModel.share_type == "specific",
                MemorySharingModel.agent_id != target_agent_id,  # 排除自己
                MemorySharingTargetModel.target_agent_id == target_agent_id
            )
        )
        specific_sharing_agents = list(specific_sharing_result.scalars().all())
        
        # 合并去重
        return list(set(all_sharing_agents + specific_sharing_agents))

