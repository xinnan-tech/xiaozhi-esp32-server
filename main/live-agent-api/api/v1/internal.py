from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db
from infra.fishaudio import get_fish_audio
from services.agent_service import agent_service
from utils.response import success_response
from schemas.agent import AgentConfigResponse

router = APIRouter()


@router.get("/agents/{agent_id}/config", summary="Get agent config for backend services")
async def get_agent_config(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    fish_client = Depends(get_fish_audio)
):
    """
    Get agent runtime configuration for xiaozhi-server
    
    This is an internal API for service-to-service communication:
    - No authentication required
    - Returns agent config with voice language info from Fish Audio
    - Used by xiaozhi-server to drive AI conversations
    
    Flow:
    1. Get agent config by agent_id
    2. If voice_id exists, fetch voice info from Fish Audio
    3. Extract language and merge into response
    """
    # Step 1: Get agent config
    agent = await agent_service.get_agent_detail(db=db, agent_id=agent_id)
    
    # Step 2: If voice_id exists, fetch language from Fish Audio
    language = None
    if agent.voice_id:
        try:
            fish_voice = await fish_client.voices.get(agent.voice_id)
            if fish_voice and hasattr(fish_voice, 'languages') and fish_voice.languages:
                # Fish Audio returns a list of languages, take the first one
                language = fish_voice.languages[0] if isinstance(fish_voice.languages, list) else fish_voice.languages
        except Exception as e:
            # If Fish Audio API fails, log but don't fail the request
            print(f"Warning: Failed to fetch voice language for {agent.voice_id}: {e}")
    
    # Step 3: Merge voice language into response
    response = AgentConfigResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        voice_id=agent.voice_id,
        language=language,
        instruction=agent.instruction,
        voice_opening=agent.voice_opening,
        voice_closing=agent.voice_closing,
    )
    
    return success_response(data=response.model_dump())

