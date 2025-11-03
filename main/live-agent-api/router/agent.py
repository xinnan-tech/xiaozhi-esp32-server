"""
Agent Router

API endpoints for Agent management.
"""

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from orm import get_db
from services.agent_service import AgentService, get_agent_service
from schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentDuplicate,
    AgentResponse,
    AgentListQuery,
    GeneratePromptRequest,
    GeneratePromptResponse,
)
from utils.response import (
    ApiResponse,
    success_response,
    error_response,
    paginated_response,
)
from templates import TemplateLoader


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/")
async def get_agent_list(
    search: Annotated[str | None, Query(description="Search keyword")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100, alias="pageSize", description="Items per page")] = 20,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Get Agent list with search and pagination (sorted by creation time desc)
    
    - **search**: Search keyword (searches in name and system prompt)
    - **page**: Page number (starting from 1)
    - **pageSize**: Number of items per page (1-100, default: 20)
    
    Returns paginated list of agents sorted by creation time (newest first) with total count.
    """
    try:
        # Create query object
        query = AgentListQuery(
            search=search,
            page=page,
            page_size=pageSize,
        )
        
        # Get service
        service = get_agent_service(db)
        
        # Get agents
        agents, total = await service.get_agent_list(query)
        
        # Convert to response format
        agent_responses = [
            AgentResponse.model_validate(agent) for agent in agents
        ]
        
        # Create paginated response
        pagination_data = paginated_response(
            items=agent_responses,
            total=total,
            page=page,
            page_size=pageSize,
        )
        
        return success_response(data=pagination_data)
        
    except Exception as e:
        logger.error(f"Error getting agent list: {str(e)}")
        return error_response(
            message=f"Failed to get agent list: {str(e)}",
            code=500
        )


@router.get("/{agent_id}")
async def get_agent_detail(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Get Agent details by ID
    
    - **agent_id**: Agent unique ID
    
    Returns detailed agent information.
    """
    try:
        service = get_agent_service(db)
        agent = await service.get_agent_by_id(agent_id)
        
        if not agent:
            return error_response(
                message=f"Agent not found: {agent_id}",
                code=404
            )
        
        agent_response = AgentResponse.model_validate(agent)
        return success_response(data=agent_response)
        
    except Exception as e:
        logger.error(f"Error getting agent detail: {str(e)}")
        return error_response(
            message=f"Failed to get agent detail: {str(e)}",
            code=500
        )


@router.post("/")
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Create a new Agent
    
    Request body:
    - **name**: Agent display name (required)
    - **template**: Agent template type (default: blank)
    - **language**: Language code, e.g., en, zh (default: en)
    - **firstMessage**: Greeting message (optional)
    - **systemPrompt**: System prompt for behavior (optional)
    - **wakeWord**: Wake word to activate agent (default: PLAUD)
    
    Returns the created agent with generated ID.
    """
    try:
        service = get_agent_service(db)
        agent = await service.create_agent(agent_data)
        
        agent_response = AgentResponse.model_validate(agent)
        return success_response(
            data=agent_response,
            message="Agent created successfully",
            code=201
        )
        
    except ValueError as e:
        # Template validation errors
        logger.warning(f"Validation error creating agent: {str(e)}")
        return error_response(
            message=str(e),
            code=400
        )
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        return error_response(
            message=f"Failed to create agent: {str(e)}",
            code=500
        )


@router.put("/{agent_id}")
async def update_agent(
    agent_id: str,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Update Agent configuration
    
    - **agent_id**: Agent unique ID
    
    Request body (all fields optional):
    - **name**: Agent display name
    - **language**: Language code
    - **firstMessage**: Greeting message
    - **systemPrompt**: System prompt for behavior
    - **wakeWord**: Wake word to activate agent
    
    Returns the updated agent information.
    """
    try:
        service = get_agent_service(db)
        agent = await service.update_agent(agent_id, agent_data)
        
        if not agent:
            return error_response(
                message=f"Agent not found: {agent_id}",
                code=404
            )
        
        agent_response = AgentResponse.model_validate(agent)
        return success_response(
            data=agent_response,
            message="Agent updated successfully"
        )
        
    except Exception as e:
        logger.error(f"Error updating agent: {str(e)}")
        return error_response(
            message=f"Failed to update agent: {str(e)}",
            code=500
        )


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Delete an Agent
    
    - **agent_id**: Agent unique ID
    
    Deletes the agent if no binding relationships exist.
    Returns success message if deleted.
    """
    try:
        service = get_agent_service(db)
        deleted = await service.delete_agent(agent_id)
        
        if not deleted:
            return error_response(
                message=f"Agent not found: {agent_id}",
                code=404
            )
        
        return success_response(
            data={"id": agent_id},
            message="Agent deleted successfully"
        )
        
    except Exception as e:
        logger.error(f"Error deleting agent: {str(e)}")
        return error_response(
            message=f"Failed to delete agent: {str(e)}",
            code=500
        )


@router.post("/{agent_id}/duplicate")
async def duplicate_agent(
    agent_id: str,
    duplicate_data: AgentDuplicate,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Duplicate an existing Agent
    
    - **agent_id**: Source agent ID to duplicate
    
    Request body:
    - **name**: Name for the duplicated agent (required)
    
    Creates a copy of the agent with a new ID and name.
    Returns the newly created agent.
    """
    try:
        service = get_agent_service(db)
        new_agent = await service.duplicate_agent(
            agent_id,
            duplicate_data.name
        )
        
        if not new_agent:
            return error_response(
                message=f"Source agent not found: {agent_id}",
                code=404
            )
        
        agent_response = AgentResponse.model_validate(new_agent)
        return success_response(
            data=agent_response,
            message="Agent duplicated successfully",
            code=201
        )
        
    except Exception as e:
        logger.error(f"Error duplicating agent: {str(e)}")
        return error_response(
            message=f"Failed to duplicate agent: {str(e)}",
            code=500
        )


@router.post("/generate-prompt")
async def generate_system_prompt(
    request: GeneratePromptRequest,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """
    Generate system prompt using AI
    
    Request body:
    - **description**: Description of the agent's purpose and requirements (required)
    - **currentPrompt**: Existing system prompt to refine or build upon (optional)
    
    Uses OpenAI to generate a professional system prompt that follows the 6-module structure:
    1. Personality - Agent's character and communication style
    2. Environment - Context and operating setting
    3. Tone - Language tone and interaction manner
    4. Goal - Primary objectives and purposes
    5. Guardrails - Rules, limitations, and ethical boundaries
    6. Tools - Available capabilities and functions
    
    If currentPrompt is provided, the AI will refine it based on the description.
    Otherwise, it creates a new prompt from scratch.
    """
    try:
        service = get_agent_service(db)
        generated_prompt = await service.generate_system_prompt(request)
        
        response_data = GeneratePromptResponse(
            systemPrompt=generated_prompt
        )
        
        return success_response(
            data=response_data,
            message="System prompt generated successfully"
        )
        
    except Exception as e:
        logger.error(f"Error generating prompt: {str(e)}")
        return error_response(
            message=f"Failed to generate prompt: {str(e)}",
            code=500
        )

