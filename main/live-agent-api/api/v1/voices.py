from typing import Optional, List
from botocore.args import logger
from fastapi import APIRouter, Depends, Query, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db
from infra.fishaudio import get_fish_audio
from services.voice_service import voice_service
from schemas.voice import ( 
    LiveAgentVoice, 
    DiscoverVoiceResponse, 
    AudioSample,
    MyVoiceResponse,
    VoiceUpdateRequest,
    VoiceAddRequest
)
from utils.response import success_response
from api.auth import get_current_user_id

import logging

router = APIRouter()

logging.getLogger(__name__)

@router.get("/discover", summary="Get Discover Voices")
async def get_discover_voices(
    title: Optional[str] = Query(None, description="Filter by voice title/name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    fish_client = Depends(get_fish_audio)
):
    """
    Get voices from Fish Audio platform (discover tab)
    - Sorted by task_count (popularity)
    - Supports filtering by title
    """
    # Get raw data from service layer
    fish_voices, has_more = await voice_service.get_discover_voices(
        fish_client=fish_client,
        title=title,
        page=page,
        page_size=page_size,
        language="en"
    )
    
    # Convert Fish Audio Voice objects to VoiceResponse in API layer
    voices = []
    for voice in fish_voices:
        samples = []
        for sample in voice.samples:
            samples.append(AudioSample(
                title=sample.title,
                text=sample.text,
                audio=sample.audio
            ))
        
        logger.info(f"Voice Tags: {voice.tags}")
            
        voices.append(LiveAgentVoice(
            voice_id=voice.id,
            name=voice.title,
            desc=voice.description,
            tags=voice.tags,
            task_count=voice.task_count,
            like_count=voice.like_count,
            samples=samples,
        ))
    
    # Build response
    voice_list = DiscoverVoiceResponse(
        voices=voices,
        has_more=has_more
    )
    
    return success_response(data=voice_list.model_dump())


@router.get("/default", summary="Get Default Voices")
async def get_default_voices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get platform default voices (default tab)
    TODO: Implementation pending PM discussion tomorrow
    """
    return success_response(data={})


@router.get("/", summary="Get My Voices")
async def get_my_voices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's custom voices (my_voices tab)
    Returns voices created/cloned by the current user
    """
    # Get raw data from service layer
    voices, count = await voice_service.get_my_voices(
        db=db,
        owner_id=current_user_id,
        page=page,
        page_size=page_size
    )
    
    # Convert VoiceModel to VoiceResponse in API layer
    voice_responses = []
    for voice in voices:
        voice_responses.append(LiveAgentVoice(
            voice_id=voice.voice_id,
            name=voice.name,
            tags=voice.tags or [],
        ))
    
    # Build response
    voice_list = MyVoiceResponse(
        voices=voice_responses,
        has_more=count > page * page_size
    )
    
    return success_response(data=voice_list.model_dump())


@router.post("/clone", summary="Clone Voice from Audio")
async def clone_voice(
    audio_file: UploadFile = File(..., description="Audio file for cloning"),
    text: Optional[str] = Form(None, description="Optional transcription text"),
    fish_client = Depends(get_fish_audio)
):
    """
    Clone a voice from uploaded audio file
    - Supports both direct audio upload and recorded audio
    - Text parameter is optional (required for recorded audio)
    - Uses Fish Audio's fast training mode (typically 30s-2min)
    """
    
    # Clone voice
    voice_id = await voice_service.clone_voice(
        fish_client=fish_client,
        audio_file=audio_file,
        text=text
    )
    
    # Build response
    return success_response(
        data={
            "voice_id": voice_id,
        },
        message="Voice cloned successfully"
    )


@router.post("/add/{voice_id}", summary="Add Fish Voice to My Voices")
async def add_voice(
    voice_id: str,
    request: VoiceAddRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    fish_client = Depends(get_fish_audio)
):
    """
    Add a Fish Audio voice to user's my voices
    - Creates a reference to the Fish Audio voice
    - Name is provided by client (from Fish voice title)
    """
    voice = await voice_service.add_voice(
        db=db,
        fish_client=fish_client,
        owner_id=current_user_id,
        voice_id=voice_id,
        name=request.name,
        desc=request.desc
    )
    
    # Build response
    return success_response(
        data=LiveAgentVoice(
            voice_id=voice.voice_id,
            name=voice.name,
        ).model_dump(exclude_none=True),
        message="Voice added successfully"
    )


@router.put("/{voice_id}", summary="Update Voice")
async def update_voice(
    voice_id: str,
    request: VoiceUpdateRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Update voice name and/or description
    - Only the voice owner can update it
    - At least one field (name or desc) must be provided
    """
    # Check if at least one field is provided
    if request.name is None and request.desc is None:
        from utils.exceptions import BadRequestException
        raise BadRequestException("At least one field (name or desc) must be provided")
    
    voice = await voice_service.update_voice(
        db=db,
        voice_id=voice_id,
        owner_id=current_user_id,
        name=request.name,
        desc=request.desc
    )
    
    return success_response(
        data=LiveAgentVoice(
            voice_id=voice.voice_id,
            name=voice.name,
            desc=voice.desc
        ).model_dump(exclude_none=True),
        message="Voice updated successfully"
    )


@router.delete("/{voice_id}", summary="Remove Voice from My Voices")
async def remove_voice(
    voice_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a voice from user's my voices
    - Only deletes the database record (reference)
    - User must own the voice
    """
    await voice_service.remove_voice(
        db=db,
        voice_id=voice_id,
        owner_id=current_user_id
    )
    
    return success_response(
        data={"voice_id": voice_id},
        message="Voice removed successfully"
    )