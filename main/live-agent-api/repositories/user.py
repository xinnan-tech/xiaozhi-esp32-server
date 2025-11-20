from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, TIMESTAMP, Index, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database import Base, utc_now


# ==================== ORM Model ====================

class UserModel(Base):
    __tablename__ = "user"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # User unique identifier (external)
    user_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    
    # User credentials and info
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    
    # Timestamps
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
        Index('idx_user_userid', 'user_id', unique=True),
        Index('idx_user_username', 'username', unique=True),
    )

    def __repr__(self):
        return f"<UserModel(id={self.id}, user_id={self.user_id})>"


# ==================== Repository (CRUD Operations) ====================

class User:
    """
    User Repository - Handles all database operations
    """

    @staticmethod
    async def get_by_user_id(db: AsyncSession, user_id: str) -> Optional[UserModel]:
        """Get user by user_id"""
        result = await db.execute(select(UserModel).where(UserModel.user_id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> Optional[UserModel]:
        """Get user by username"""
        result = await db.execute(select(UserModel).where(UserModel.username == username))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: str,
        username: str,
        hashed_password: str
    ) -> UserModel:
        """Create a new user"""
        user = UserModel(
            user_id=user_id,
            username=username,
            password=hashed_password,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_password(
        db: AsyncSession,
        user_id: str,
        new_hashed_password: str
    ) -> Optional[UserModel]:
        """Update user password"""
        user = await User.get_by_user_id(db, user_id)
        if not user:
            return None
        
        user.password = new_hashed_password
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def is_username_taken(db: AsyncSession, username: str) -> bool:
        """Check if username is already taken"""
        user = await User.get_by_username(db, username)
        return user is not None

