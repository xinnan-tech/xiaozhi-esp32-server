from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db
from infra.fishaudio import get_fish_audio
from services.agent_service import agent_service
from services.device_service import device_service
from utils.response import success_response
from schemas.agent import AgentConfigResponse
from schemas.device import DefaultAgentResponse, DeviceAgentResolveResponse
from fastapi import Query

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


@router.get("/devices/{device_id}/agent-by-wake", summary="Resolve agent by wake word or default")
async def resolve_agent_by_wake(
    device_id: str,
    wake_word: str | None = Query(None, description="Wake word to match"),
    db: AsyncSession = Depends(get_db),
    fish_client = Depends(get_fish_audio),
):
    """
    Resolve device agent by wake word; fallback to default binding.
    Returns agent config for runtime consumption.
    """
    resolved = await device_service.resolve_agent_by_wake_word(
        db=db,
        device_id=device_id,
        wake_word=wake_word,
    )

    # enrich language via Fish Audio if voice_id exists
    agent_cfg = resolved.agent_config
    language = agent_cfg.language
    if agent_cfg.voice_id and language is None:
        try:
            fish_voice = await fish_client.voices.get(agent_cfg.voice_id)
            if fish_voice and hasattr(fish_voice, "languages") and fish_voice.languages:
                language = (
                    fish_voice.languages[0]
                    if isinstance(fish_voice.languages, list)
                    else fish_voice.languages
                )
        except Exception:
            language = None
    agent_cfg.language = language

    return success_response(
        data=DeviceAgentResolveResponse(
            device_id=resolved.device_id,
            agent_id=resolved.agent_id,
            owner_id=resolved.owner_id,  # Device owner's user_id for memory storage
            is_default=resolved.is_default,
            match_type=resolved.match_type,
            agent_config=agent_cfg,
        ).model_dump()
    )


@router.get("/devices/{device_id}/default-agent", summary="Get device default agent (internal)")
async def get_default_agent(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    fish_client = Depends(get_fish_audio),
):
    """
    Get default agent binding for a device (fallback to latest).
    """
    binding, agent = await device_service.get_default_agent(db=db, device_id=device_id)

    language = None
    if agent.voice_id:
        try:
            fish_voice = await fish_client.voices.get(agent.voice_id)
            if fish_voice and hasattr(fish_voice, "languages") and fish_voice.languages:
                language = (
                    fish_voice.languages[0]
                    if isinstance(fish_voice.languages, list)
                    else fish_voice.languages
                )
        except Exception:
            language = None

    agent_cfg = AgentConfigResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        voice_id=agent.voice_id,
        language=language,
        instruction=agent.instruction,
        voice_opening=agent.voice_opening,
        voice_closing=agent.voice_closing,
    )

    return success_response(
        data=DefaultAgentResponse(
            device_id=device_id,
            agent=agent_cfg,
            is_default=binding.is_default,
        ).model_dump()
    )

