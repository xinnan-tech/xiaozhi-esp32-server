from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db
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

