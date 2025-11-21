from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy import String, Text, TIMESTAMP, ForeignKey, Index, select, func, update
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

from infra.database import Base, utc_now


# ==================== ORM Model ====================

class VoiceModel(Base):
    __tablename__ = "voices"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Fish Audio voice ID (not unique, can be shared by multiple users)
    voice_id: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Foreign key to user table (user_id)
    owner_id: Mapped[str] = mapped_column(
        String(50), 
        ForeignKey("user.user_id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Voice info
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    desc: Mapped[str] = mapped_column(Text, nullable=False)
    
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
        Index('idx_voices_voice_id', 'voice_id'),
        Index('idx_voices_owner_id', 'owner_id'),
        Index('idx_voices_created_at', 'created_at'),
        # Composite unique constraint: same voice can be added by different users
        Index('uk_voices_owner_voice', 'voice_id', 'owner_id', unique=True),
    )

    def __repr__(self):
        return f"<VoiceModel(id={self.id}, voice_id={self.voice_id}, name={self.name})>"


# ==================== Repository (CRUD Operations) ====================

class Voice:
    """
    Voice Repository - Handles all database operations
    """
    
    @staticmethod
    async def get_by_id(db: AsyncSession, voice_id: str) -> Optional[VoiceModel]:
        """Get voice by voice_id"""
        result = await db.execute(select(VoiceModel).where(VoiceModel.voice_id == voice_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list(
        db: AsyncSession,
        owner_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> Tuple[List[VoiceModel], Optional[str], bool]:
        """
        Get voices with cursor-based pagination
        
        Args:
            db: Database session
            owner_id: Filter by owner ID
            cursor: ISO datetime string of last item's created_at
            limit: Number of items to return
            
        Returns:
            (voices, next_cursor, has_more)
        """
        query = select(VoiceModel)
        
        if owner_id:
            # All voices accessible by user 
            query = query.where(
                VoiceModel.owner_id == owner_id
            )
        
        # Apply cursor filter if provided
        if cursor:
            try:
                cursor_time = datetime.fromisoformat(cursor)
                # Get records created before cursor time
                query = query.where(VoiceModel.created_at < cursor_time)
            except (ValueError, TypeError):
                # Invalid cursor, ignore and start from beginning
                pass
        
        # Order by created_at DESC, voice_id DESC for stable sorting
        # Fetch limit + 1 to check if there are more records
        query = query.order_by(
            VoiceModel.created_at.desc(),
            VoiceModel.voice_id.desc()
        ).limit(limit + 1)
        
        result = await db.execute(query)
        voices = list(result.scalars().all())
        
        # Check if there are more records
        has_more = len(voices) > limit
        if has_more:
            voices = voices[:limit]
        
        # Generate next cursor from last item
        next_cursor = None
        if has_more and voices:
            next_cursor = voices[-1].created_at.isoformat()
        
        return voices, next_cursor, has_more
    
    async def count(
        db: AsyncSession,
        owner_id: Optional[str] = None
    ) -> int:
        """Count voices with owner_id"""
        stmt = (
            select(func.count())
            .select_from(VoiceModel)
            .where(VoiceModel.owner_id == owner_id)
        )
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def get_by_voice_and_owner(
        db: AsyncSession,
        voice_id: str,
        owner_id: str
    ) -> Optional[VoiceModel]:
        """Get voice by voice_id and owner_id (composite key)"""
        stmt = (
            select(VoiceModel)
            .where(VoiceModel.voice_id == voice_id)
            .where(VoiceModel.owner_id == owner_id)
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        voice_id: str,
        owner_id: str,
        name: str,
        desc: str
    ) -> VoiceModel:
        """Create a new voice"""
        voice = VoiceModel(
            voice_id=voice_id,
            owner_id=owner_id,
            name=name,
            desc=desc
        )
        db.add(voice)
        await db.commit()
        await db.refresh(voice)
        return voice
    
    @staticmethod
    async def update(
        db: AsyncSession,
        voice_id: str,
        owner_id: str,
        name: str,
        desc: str
    ) -> VoiceModel:
        """Update a voice"""
        stmt = (
            update(VoiceModel)
            .where(VoiceModel.voice_id == voice_id)
            .where(VoiceModel.owner_id == owner_id)
            .values(name=name, desc=desc)
            .returning(VoiceModel)
        )
        result =await db.execute(stmt)
        await db.commit()
        return result.scalar_one()
    
    @staticmethod
    async def delete(
        db: AsyncSession,
        voice_id: str,
        owner_id: str
    ) -> bool:
        """
        Delete a voice (only if owned by user)
        
        Returns:
            True if deleted, False if not found or not owned
        """
        result = await db.execute(
            select(VoiceModel).where(
                VoiceModel.voice_id == voice_id,
                VoiceModel.owner_id == owner_id
            )
        )
        voice = result.scalar_one_or_none()
        
        if not voice:
            return False
        
        await db.delete(voice)
        await db.commit()
        return True

