"""
Agent Service

Business logic layer for Agent operations.
Uses Repository pattern for data access.
"""

import logging
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from orm.agent import Agent, AgentRepository
from schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentListQuery,
    GeneratePromptRequest,
)
from utils import id_generator
from templates import TemplateLoader
from config.settings import settings


logger = logging.getLogger(__name__)
BLANK_TEMPLATE = "blank"
SYSTEM_PROMPT_INSTRUCTION = """
You are an AI assistant that helps create system prompts for voice assistant agents.
Generate a clear, professional system prompt that strictly follows this 6-module structure:
1. **Personality**: Define the agent's character, traits, and communication style
2. **Environment**: Describe the context and setting where the agent operates
3. **Tone**: Specify the language tone and manner of interaction
4. **Goal**: State the primary objectives and purposes of the agent
5. **Guardrails**: Define rules, limitations, and ethical boundaries
6. **Tools**: List available capabilities, APIs, or functions the agent can use
Each section should be clearly labeled with markdown headers (##). 
The prompt should be comprehensive yet concise, suitable for a voice assistant.
"""

class AgentService:
    """Service class for Agent business logic"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize Agent service
        
        Args:
            db: Database session
        """
        self.repo = AgentRepository(db)
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def get_agent_list(
        self,
        query: AgentListQuery
    ) -> tuple[list[Agent], int]:
        """
        Get paginated list of agents with optional search (sorted by creation time desc)
        
        Args:
            query: Query parameters for filtering and pagination
            
        Returns:
            Tuple of (agents list, total count)
        """
        agents, total = await self.repo.find_all(
            search=query.search,
            page=query.page,
            page_size=query.page_size,
        )
        
        logger.info(
            f"Retrieved {len(agents)} agents (page {query.page}, total {total})"
        )
        
        return agents, total
    
    async def get_agent_by_id(self, agent_id: str) -> Optional[Agent]:
        """
        Get agent by ID
        
        Args:
            agent_id: Agent unique ID
            
        Returns:
            Agent instance or None if not found
        """
        agent = await self.repo.find_by_id(agent_id)
        
        if agent:
            logger.info(f"Retrieved agent: {agent_id}")
        else:
            logger.warning(f"Agent not found: {agent_id}")
        
        return agent
    
    async def create_agent(self, agent_data: AgentCreate) -> Agent:
        """
        Create a new agent
        
        Args:
            agent_data: Agent creation data
            
        Returns:
            Created agent instance
            
        Raises:
            ValueError: If template does not exist
        """
        # 1. Generate unique ID
        agent_id = id_generator.generate()
        
        # 2. Create blank agent first
        agent = Agent(
            id=agent_id,
            name=agent_data.name,
            language=agent_data.language,
            first_message=agent_data.first_message,
            system_prompt=agent_data.system_prompt,
            wake_word=agent_data.wake_word,
        )
        
        # 3. If not blank template, load and populate from template
        if agent_data.template != BLANK_TEMPLATE:
            try:
                template = TemplateLoader.load(agent_data.template)
                
                if template is None:
                    raise ValueError(f"Failed to load template: {agent_data.template}")
                
                # Populate agent from template (template values are applied if user didn't provide)
                agent.language = template.language
                agent.first_message = template.greeting
                agent.system_prompt = template.profile
                agent.wake_word = template.wake_word
                
                logger.info(f"Populated agent from template: {agent_data.template}")
                
            except ValueError as e:
                logger.error(f"Error loading template: {e}")
                raise
        
        # Persist to database
        agent = await self.repo.save(agent)
        
        logger.info(f"Created agent: {agent_id} ({agent.name})")
        
        return agent
    
    async def update_agent(
        self,
        agent_id: str,
        agent_data: AgentUpdate
    ) -> Optional[Agent]:
        """
        Update agent configuration
        
        Args:
            agent_id: Agent unique ID
            agent_data: Agent update data
            
        Returns:
            Updated agent instance or None if not found
        """
        # Get existing agent
        agent = await self.repo.find_by_id(agent_id)
        if not agent:
            return None
        
        # Business logic: Update fields
        update_data = agent_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            # Convert camelCase to snake_case
            db_field = field.replace("firstMessage", "first_message")
            db_field = db_field.replace("systemPrompt", "system_prompt")
            db_field = db_field.replace("wakeWord", "wake_word")
            
            if hasattr(agent, db_field):
                setattr(agent, db_field, value)
        
        # Business logic: Update timestamp
        agent.updated_at = datetime.now(timezone.utc)
        
        # Persist changes
        agent = await self.repo.save(agent)
        
        logger.info(f"Updated agent: {agent_id}")
        
        return agent
    
    async def delete_agent(self, agent_id: str) -> bool:
        """
        Delete an agent
        
        Args:
            agent_id: Agent unique ID
            
        Returns:
            True if deleted, False if not found
        """
        agent = await self.repo.find_by_id(agent_id)
        if not agent:
            return False
        
        # TODO: Business logic - Check for binding relationships
        # For now, just delete the agent
        # In production, should check if agent has bindings and handle accordingly
        
        await self.repo.delete(agent)
        
        logger.info(f"Deleted agent: {agent_id}")
        
        return True
    
    async def duplicate_agent(
        self,
        agent_id: str,
        new_name: str
    ) -> Optional[Agent]:
        """
        Duplicate an existing agent
        
        Args:
            agent_id: Source agent ID
            new_name: Name for the duplicated agent
            
        Returns:
            New agent instance or None if source not found
        """
        # Get source agent
        source_agent = await self.repo.find_by_id(agent_id)
        if not source_agent:
            return None
        
        # Business logic: Create duplicate with new ID and name
        new_id = id_generator.generate()
        duplicate_agent = Agent(
            id=new_id,
            name=new_name,
            language=source_agent.language,
            first_message=source_agent.first_message,
            system_prompt=source_agent.system_prompt,
            wake_word=source_agent.wake_word,
        )
        
        # Persist to database
        duplicate_agent = await self.repo.save(duplicate_agent)
        
        logger.info(
            f"Duplicated agent {agent_id} to {new_id} ({new_name})"
        )
        
        return duplicate_agent
    
    async def generate_system_prompt(
        self,
        request: GeneratePromptRequest
    ) -> str:
        """
        Generate system prompt using AI
        
        Args:
            request: Prompt generation request with description and optional existing prompt
            
        Returns:
            Generated system prompt following the 6-module structure
        """
        logger.info(f"Generating prompt for: {request.description}")
        
        try:
            system_instruction = SYSTEM_PROMPT_INSTRUCTION
            
            # Build user message based on whether existing prompt is provided
            if request.current_prompt:
                user_message = (
                    f"I need help refining or regenerating a system prompt.\n\n"
                    f"**User Requirements/Description:**\n{request.description}\n\n"
                    f"**Current Prompt:**\n{request.current_prompt}\n\n"
                    f"Please create an improved system prompt that incorporates the requirements "
                    f"and builds upon the existing prompt, following the 6-module structure."
                )
            else:
                user_message = (
                    f"Create a new system prompt for: {request.description}\n\n"
                    f"Please structure it according to the 6 modules (Personality, Environment, Tone, Goal, Guardrails, Tools)."
                )
            
            # Create prompt using OpenAI API
            # Note: Using chat.completions for now, ready to migrate to response.create when available
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": system_instruction
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                temperature=0.7,
                max_tokens=1500,
            )
            
            generated_prompt = response.choices[0].message.content.strip()
            
            logger.info("Successfully generated system prompt with 6-module structure")
            
            return generated_prompt
            
        except Exception as e:
            logger.error(f"Error generating prompt: {str(e)}")
            raise


def get_agent_service(db: AsyncSession) -> AgentService:
    """
    Dependency function to get Agent service
    
    Args:
        db: Database session
        
    Returns:
        AgentService instance
    """
    return AgentService(db)
