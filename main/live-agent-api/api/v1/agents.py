from typing import Optional
from fastapi import APIRouter, Depends, Query, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db, get_s3
from services.agent_service import agent_service
from utils.response import success_response
from api.auth import get_current_user_id

router = APIRouter()


@router.get("", summary="Get user's agent list")
async def get_agent_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=20),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get user's agent list"""
    agent_list = await agent_service.get_agent_list(
        db=db,
        owner_id=current_user_id,
        page=page,
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
    return success_response(data=agent.model_dump())


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

