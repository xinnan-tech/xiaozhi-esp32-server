from typing import Optional
from fastapi import APIRouter, Depends, Query, Form, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db, get_s3
from infra.openai import get_openai
from services.agent_service import agent_service
from services.llm_service import llm_service
from utils.response import success_response
from api.auth import get_current_user_id
from schemas.agent import AgentResponse
from config import get_logger
import base64
from fastapi import HTTPException
import asyncio

logger = get_logger(__name__)
router = APIRouter()


@router.get("", summary="Get user's agent list")
async def get_agent_list(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    page_size: int = Query(10, ge=1, le=20, description="Number of items per page"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's agent list with cursor-based pagination
    
    Cursor-based pagination prevents data drift when creating/deleting agents:
    - **First request**: No cursor parameter needed
    - **Subsequent requests**: Use `next_cursor` from previous response
    - **Returns**: List of agents with `next_cursor` and `has_more` flag
    
    Agents are ordered by creation time (newest first).
    """
    agent_list = await agent_service.get_agent_list(
        db=db,
        owner_id=current_user_id,
        cursor=cursor,
        page_size=page_size
    )
    return success_response(data=agent_list.model_dump())


@router.get("/{agent_id}", summary="Get Agent Detail")
async def get_agent_detail(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get agent detail"""
    agent = await agent_service.get_agent_detail(db=db, agent_id=agent_id)


    agent_response = AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        avatar_url=agent.avatar_url,
        description=agent.description,
        voice_id=agent.voice_id,
        instruction=agent.instruction,
        voice_opening=agent.voice_opening,
        voice_closing=agent.voice_closing,
        created_at=agent.created_at,
    )
    return success_response(data=agent_response.model_dump())


@router.post("", summary="Create Agent")
async def create_agent(
    name: str = Form(...),
    instruction: str = Form(...),
    description: Optional[str] = Form(None),
    voice_id: Optional[str] = Form(None),
    voice_opening: Optional[str] = Form(None),
    voice_closing: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    s3 = Depends(get_s3)
):
    """Create a new agent"""
    agent = await agent_service.create_agent(
        db=db,
        s3=s3,
        owner_id=current_user_id,
        name=name,
        instruction=instruction,
        description=description,
        voice_id=voice_id,
        voice_opening=voice_opening,
        voice_closing=voice_closing,
        avatar=avatar
    )
    return success_response(data=agent.model_dump())


@router.put("/{agent_id}", summary="Update Agent")
async def update_agent(
    agent_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    voice_id: Optional[str] = Form(None),
    instruction: Optional[str] = Form(None),
    voice_opening: Optional[str] = Form(None),
    voice_closing: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    s3 = Depends(get_s3)
):
    """Update agent"""
    agent = await agent_service.update_agent(
        db=db,
        s3=s3,
        agent_id=agent_id,
        owner_id=current_user_id,
        name=name,
        description=description,
        voice_id=voice_id,
        instruction=instruction,
        voice_opening=voice_opening,
        voice_closing=voice_closing,
        avatar=avatar
    )
    return success_response(data=agent.model_dump())


@router.delete("/{agent_id}", summary="Delete Agent")
async def delete_agent(
    agent_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    s3 = Depends(get_s3)
):
    """Delete agent"""
    await agent_service.delete_agent(
        db=db,
        s3=s3,
        agent_id=agent_id,
        owner_id=current_user_id
    )
    return success_response(data={}, message="Agent deleted successfully")


@router.post("/persona", summary="Generate or Optimize Agent Persona")
async def generate_persona(
    name: str = Form(..., description="Agent name (required)"),
    instruction: Optional[str] = Form(None, description="Existing instruction (required for optimize mode)"),
    avatar: Optional[UploadFile] = File(None, description="Optional avatar image"),
    mode: str = Form("quick", description="Mode: 'quick' (non-streaming) or 'optimize' (streaming)"),
    current_user_id: str = Depends(get_current_user_id),
    openai_client = Depends(get_openai)
):
    """
    Generate or optimize agent persona
    
    **Modes:**
    - `quick`: Fast non-streaming, returns JSON with instruction + voice_opening + voice_closing (for initial creation)
    - `optimize`: Streaming, returns detailed instruction text (for iterative refinement)
    
    **Parameters:**
    - **name**: Agent name (required) - e.g., "Dave", "Elon Musk", "Labubu"
    - **instruction**: Existing instruction text (required for optimize mode)
    - **avatar**: Optional avatar image to inform persona's visual characteristics
    - **mode**: "quick" (default) or "optimize"
    
    **Returns:**
    - quick mode: `{"code": 0, "data": {"instruction": "...", "voice_opening": "...", "voice_closing": "..."}}`
    - optimize mode: Streaming text with enhanced instruction
    """
    
    # Process avatar if provided
    avatar_base64 = None
    avatar_media_type = None
    
    if avatar:
        try:
            content = await avatar.read()
            avatar_base64 = base64.b64encode(content).decode("utf-8")
            avatar_media_type = avatar.content_type or "image/jpeg"
        except Exception as e:
            logger.warning(f"Failed to process avatar: {e}")
    
    if mode == "optimize":
        # Optimize mode: streaming with SSE format, requires existing instruction
        if not instruction:
            raise HTTPException(status_code=400, detail="instruction is required for optimize mode")
        
        async def stream_generator():
            try:
                async for chunk in llm_service.optimize_persona_stream(
                    openai_client=openai_client,
                    name=name,
                    instruction=instruction,
                    avatar_base64=avatar_base64,
                    avatar_media_type=avatar_media_type
                ):
                    # SSE format: data: <content>\n\n
                    yield f"data: {chunk}\n\n"
            except Exception as e:
                logger.error(f"Persona optimization failed: {e}")
                yield f"data: [ERROR] {str(e)}\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream"
        )
    else:
        # Quick mode: non-streaming, returns JSON
        try:
            result = await llm_service.generate_persona_quick(
                openai_client=openai_client,
                name=name,
                avatar_base64=avatar_base64,
                avatar_media_type=avatar_media_type
            )
            return success_response(data=result)
        except Exception as e:
            logger.error(f"Persona generation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

