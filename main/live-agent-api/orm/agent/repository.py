"""
Agent Repository

Data access layer for Agent entity.
Encapsulates all database operations for Agent.
"""

from typing import Optional
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from orm.agent.model import Agent


class AgentRepository:
    """Repository for Agent data access operations"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session
        
        Args:
            db: SQLAlchemy async session
        """
        self.db = db
    
    async def find_by_id(self, agent_id: str) -> Optional[Agent]:
        """
        Find agent by ID
        
        Args:
            agent_id: Agent unique ID
            
        Returns:
            Agent instance or None if not found
        """
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def find_all(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Agent], int]:
        """
        Find all agents with filtering, pagination and sorting
        
        Args:
            search: Search keyword (searches in name and system_prompt)
            page: Page number (starting from 1)
            page_size: Number of items per page
            sort_by: Field to sort by
            sort_order: Sort direction ('asc' or 'desc')
            
        Returns:
            Tuple of (agents list, total count)
        """
        # Build base query
        stmt = select(Agent)
        
        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Agent.name.ilike(search_pattern),
                    Agent.system_prompt.ilike(search_pattern),
                )
            )
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Apply sorting
        sort_column = getattr(Agent, sort_by, Agent.created_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())
        
        # Apply pagination
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        
        # Execute query
        result = await self.db.execute(stmt)
        agents = list(result.scalars().all())
        
        return agents, total
    
    async def save(self, agent: Agent) -> Agent:
        """
        Save or update agent
        
        Args:
            agent: Agent instance to save
            
        Returns:
            Saved agent instance
        """
        self.db.add(agent)
        await self.db.flush()
        await self.db.refresh(agent)
        return agent
    
    async def delete(self, agent: Agent) -> None:
        """
        Delete agent
        
        Args:
            agent: Agent instance to delete
        """
        await self.db.delete(agent)
        await self.db.flush()
    
    async def exists(self, agent_id: str) -> bool:
        """
        Check if agent exists
        
        Args:
            agent_id: Agent unique ID
            
        Returns:
            True if agent exists, False otherwise
        """
        stmt = select(func.count()).where(Agent.id == agent_id)
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count > 0

