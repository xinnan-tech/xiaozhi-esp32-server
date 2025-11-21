from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db
from services.agent_service import agent_service
from utils.response import success_response

router = APIRouter()


@router.get("/agents/{agent_id}/config", summary="Get a specified agent's config")
async def get_agent_config(
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get agent configuration for xiaozhi-server"""
    config = await agent_service.get_agent_config(db=db, agent_id=agent_id)
    return success_response(data=config.model_dump())

