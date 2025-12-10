from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from repositories import AgentModel, Agent, AgentTemplate, FileRepository
from utils.exceptions import NotFoundException, ForbiddenException
from utils.ulid import generate_agent_id
from schemas.agent import (
    AgentResponse, 
    AgentListResponse, 
    AgentTemplateResponse,
    AgentConfigResponse,
    AgentWithLatestMessage
)
from utils.ulid import generate_template_id


class AgentService:
    """Agent service layer"""
    
    async def get_templates(self, db: AsyncSession) -> List[AgentTemplateResponse]:
        """Get all agent templates"""
        templates = await AgentTemplate.get_all(db)
        return [AgentTemplateResponse.model_validate(t) for t in templates]

    async def create_template(
        self,
        db: AsyncSession,
        s3,
        name: str,
        description: str,
        voice_id: str,
        instruction: str,
        voice_opening: str,
        voice_closing: str,
        avatar: UploadFile
    ) -> AgentTemplateResponse:
        """Create a new agent template (all fields required)"""
        # Generate template_id
        template_id = generate_template_id()
        
        # Upload avatar
        avatar_url = await FileRepository.upload_avatar(s3, avatar, template_id)
        
        template = await AgentTemplate.create(
            db=db,
            template_id=template_id,
            name=name,
            avatar_url=avatar_url,
            description=description,
            voice_id=voice_id,
            instruction=instruction,
            voice_opening=voice_opening,
            voice_closing=voice_closing
        )
        return AgentTemplateResponse.model_validate(template)
    
    async def get_agent_list(
        self, 
        db: AsyncSession, 
        owner_id: str,
        cursor: Optional[str] = None,
        page_size: int = 10
    ) -> AgentListResponse:
        """
        Get user's agent list with cursor-based pagination, ordered by latest message time
        
        Args:
            db: Database session
            owner_id: User ID
            cursor: Pagination cursor (ISO datetime string of sort_time)
            page_size: Number of items per page
            
        Returns:
            AgentListResponse with agents (including latest message), next_cursor, and has_more
        """
        rows, next_cursor, has_more = await Agent.get_agents_with_latest_message(
            db, 
            owner_id=owner_id, 
            cursor=cursor,
            limit=page_size
        )
        
        # Process rows into response format
        agents = []
        for row in rows:
            agent = row[0]  # AgentModel instance
            
            # Extract text content from latest message if exists
            latest_message_text = None
            if row.latest_message_content:
                for item in row.latest_message_content:
                    if item.get('message_type') == 'text':
                        latest_message_text = item.get('message_content')
                        break
            
            agents.append(AgentWithLatestMessage(
                agent_id=agent.agent_id,
                name=agent.name,
                avatar_url=agent.avatar_url,
                last_activity_time=row.sort_time,
                latest_message_text=latest_message_text
            ))
        
        return AgentListResponse(
            agents=agents,
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

    async def verify_ownership(
        self,
        db: AsyncSession,
        agent_id: str,
        owner_id: str
    ) -> AgentModel:
        """
        Verify agent exists and belongs to user
        
        Args:
            db: Database session
            agent_id: Agent ID
            owner_id: Expected owner user ID
            
        Returns:
            AgentModel if verification passes
            
        Raises:
            NotFoundException: If agent not found
            ForbiddenException: If user doesn't own the agent
        """
        agent = await Agent.get_by_id(db, agent_id)
        if not agent:
            raise NotFoundException("Agent not found")

        if agent.owner_id != owner_id:
            raise ForbiddenException("You don't have permission to access this agent")
        
        return agent
    
    async def get_bindable_agents(
        self,
        db: AsyncSession,
        owner_id: str
    ) -> List[AgentModel]:
        """
        Get agents that can be bound to device (must have wake_word configured)
        
        Args:
            db: Database session
            owner_id: User ID
            
        Returns:
            List of agents with wake_word configured
        """
        return await Agent.get_bindable_agents(db, owner_id)
    
    async def is_voice_bound(self, db: AsyncSession, voice_id: str) -> bool:
        """
        Check if a voice is bound to any agent
        
        Args:
            db: Database session
            voice_id: Voice ID to check
            
        Returns:
            True if voice is bound to at least one agent
        """
        return await Agent.is_voice_bound(db, voice_id)

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
        wake_word: Optional[str] = None,
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
            voice_closing=voice_closing,
            wake_word=wake_word
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
        wake_word: Optional[str] = None,
        avatar: Optional[UploadFile] = None
    ) -> AgentResponse:
        """Update agent"""
        # Get existing agent
        agent = await Agent.get_by_id(db, agent_id)
        if not agent:
            raise NotFoundException("Agent not found")
        
        # Check ownership
        if agent.owner_id != owner_id:
            raise ForbiddenException("You don't have permission to update this agent")
        
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
        if wake_word is not None:
            update_data['wake_word'] = wake_word
        
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
            raise ForbiddenException("You don't have permission to delete this agent")
        
        # Delete avatar from S3 if exists
        if agent.avatar_url:
            await FileRepository.delete(s3, agent.avatar_url)
        
        # Delete agent
        await Agent.delete(db, agent_id)
        


agent_service = AgentService()

