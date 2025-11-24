from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from repositories import AgentModel, Agent, AgentTemplate, FileRepository
from utils.exceptions import NotFoundException, BadRequestException
from utils.ulid import generate_agent_id
from schemas.agent import (
    AgentResponse, 
    AgentListResponse, 
    AgentTemplateResponse,
    AgentConfigResponse
)
class AgentService:
    """Agent service layer"""
    
    async def get_templates(self, db: AsyncSession) -> List[AgentTemplateResponse]:
        """Get all agent templates"""
        templates = await AgentTemplate.get_all(db)
        return [AgentTemplateResponse.model_validate(t) for t in templates]
    
    async def get_agent_list(
        self, 
        db: AsyncSession, 
        owner_id: str,
        cursor: Optional[str] = None,
        page_size: int = 10
    ) -> AgentListResponse:
        """
        Get user's agent list with cursor-based pagination
        
        Args:
            db: Database session
            owner_id: User ID
            cursor: Pagination cursor (ISO datetime string)
            page_size: Number of items per page
            
        Returns:
            AgentListResponse with agents, next_cursor, and has_more
        """
        agents, next_cursor, has_more = await Agent.get_agents_by_owner(
            db, 
            owner_id=owner_id, 
            cursor=cursor,
            limit=page_size
        )
        
        agent_responses = [AgentResponse.model_validate(a) for a in agents]
        return AgentListResponse(
            agents=agent_responses,
            next_cursor=next_cursor,
            has_more=has_more
        )
    
    async def get_agent_detail(
        self, 
        db: AsyncSession, 
        agent_id: str
    ) -> AgentModel:
        """Get agent detail"""
        agent = await Agent.get_by_id(db, agent_id)
        if not agent:
            raise NotFoundException("Agent not found")
        
        return agent
    
    async def create_agent(
        self,
        db: AsyncSession,
        s3,
        owner_id: str,
        name: str,
        instruction: str,
        description: Optional[str] = None,
        voice_id: Optional[str] = None,
        voice_opening: Optional[str] = None,
        voice_closing: Optional[str] = None,
        avatar: Optional[UploadFile] = None
    ) -> AgentResponse:
        """Create a new agent"""
        # Generate agent_id first
        agent_id = generate_agent_id()
        
        # Upload avatar if provided
        avatar_url = None
        if avatar:
            avatar_url = await FileRepository.upload_avatar(s3, avatar, agent_id)
        
        # Create agent
        agent = await Agent.create(
            db=db,
            agent_id=agent_id,
            owner_id=owner_id,
            name=name,
            instruction=instruction,
            avatar_url=avatar_url,
            description=description,
            voice_id=voice_id,
            voice_opening=voice_opening,
            voice_closing=voice_closing
        )
        
        return AgentResponse.model_validate(agent)
    
    async def update_agent(
        self,
        db: AsyncSession,
        s3,  # S3 client from dependency injection
        agent_id: str,
        owner_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        voice_id: Optional[str] = None,
        instruction: Optional[str] = None,
        voice_opening: Optional[str] = None,
        voice_closing: Optional[str] = None,
        avatar: Optional[UploadFile] = None
    ) -> AgentResponse:
        """Update agent"""
        # Get existing agent
        agent = await Agent.get_by_id(db, agent_id)
        if not agent:
            raise NotFoundException("Agent not found")
        
        # Check ownership
        if agent.owner_id != owner_id:
            raise BadRequestException("You don't have permission to update this agent")
        
        # Prepare update data
        update_data = {}
        if name is not None:
            update_data['name'] = name
        if description is not None:
            update_data['description'] = description
        if voice_id is not None:
            update_data['voice_id'] = voice_id
        if instruction is not None:
            update_data['instruction'] = instruction
        if voice_opening is not None:
            update_data['voice_opening'] = voice_opening
        if voice_closing is not None:
            update_data['voice_closing'] = voice_closing
        
        # Upload new avatar if provided (using agent_id as filename)
        # Note: Since we use agent_id as filename, uploading will automatically
        # overwrite the old avatar file, so no need to delete it first
        if avatar:
            avatar_url = await FileRepository.upload_avatar(s3, avatar, agent_id)
            update_data['avatar_url'] = avatar_url
        
        # Update agent
        updated_agent = await Agent.update(db, agent_id, **update_data)
        if not updated_agent:
            raise NotFoundException("Agent not found")
        
        return AgentResponse.model_validate(updated_agent)
    
    async def delete_agent(
        self, 
        db: AsyncSession,
        s3,  # S3 client from dependency injection
        agent_id: str,
        owner_id: str
    ) -> None:
        """Delete agent"""
        # Get agent
        agent = await Agent.get_by_id(db, agent_id)
        if not agent:
            raise NotFoundException("Agent not found")
        
        # Check ownership
        if agent.owner_id != owner_id:
            raise BadRequestException("You don't have permission to delete this agent")
        
        # Delete avatar from S3 if exists
        if agent.avatar_url:
            await FileRepository.delete(s3, agent.avatar_url)
        
        # Delete agent
        await Agent.delete(db, agent_id)
        


agent_service = AgentService()

