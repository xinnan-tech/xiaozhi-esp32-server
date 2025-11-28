from fastapi import APIRouter, Depends, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db, get_s3
from services.agent_service import agent_service
from utils.response import success_response

router = APIRouter()


@router.get("", summary="Get Agent Templates")
async def get_templates(
    db: AsyncSession = Depends(get_db)
):
    """Get all agent templates"""
    templates = await agent_service.get_templates(db)
    return success_response(data={"templates": [t.model_dump() for t in templates]})


@router.post("", summary="Create Agent Template")
async def create_template(
    name: str = Form(...),
    description: str = Form(...),
    voice_id: str = Form(...),
    instruction: str = Form(...),
    voice_opening: str = Form(...),
    voice_closing: str = Form(...),
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    s3 = Depends(get_s3)
):
    """
    Create a new agent template (all fields required)
    
    - **name**: Template name
    - **description**: Template description
    - **voice_id**: Fish Audio voice ID
    - **instruction**: System prompt for the agent
    - **voice_opening**: Opening message
    - **voice_closing**: Closing message
    - **avatar**: Avatar image file
    """
    template = await agent_service.create_template(
        db=db,
        s3=s3,
        name=name,
        description=description,
        voice_id=voice_id,
        instruction=instruction,
        voice_opening=voice_opening,
        voice_closing=voice_closing,
        avatar=avatar
    )
    return success_response(data=template.model_dump())

