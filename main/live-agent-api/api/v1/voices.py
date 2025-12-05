from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Form, File, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from infra import get_db, get_s3
from infra.fishaudio import get_fish_audio
from infra.openai import get_openai
from services.voice_service import voice_service
from services.llm_service import llm_service
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
from config import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/discover", summary="Get Discover Voices")
async def get_discover_voices(
    title: Optional[str] = Query(None, description="Filter by voice title/name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    language: Optional[str] = Query(None, description="Filter by language"),
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
        language=language
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
            samples=samples,
            created_at=voice.created_at,
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
    cursor: Optional[str] = Query(None, description="Pagination cursor (ISO datetime from previous response)"),
    page_size: int = Query(10, ge=1, le=50, description="Number of items per page"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's custom voices with cursor-based pagination
    
    Cursor-based pagination prevents data drift when adding/removing voices:
    - **First request**: No cursor parameter needed
    - **Subsequent requests**: Use `next_cursor` from previous response
    - **Returns**: List of voices with `next_cursor` and `has_more` flag
    
    Voices are ordered by creation time (newest first).
    Returns voices created/cloned/added by the current user.
    """
    # Get raw data from service layer
    voices, next_cursor, has_more = await voice_service.get_my_voices(
        db=db,
        owner_id=current_user_id,
        cursor=cursor,
        page_size=page_size
    )
    
    # Convert VoiceModel to VoiceResponse in API layer
    voice_responses = []
    for voice in voices:
        voice_responses.append(LiveAgentVoice(
            voice_id=voice.voice_id,
            name=voice.name,
            desc=voice.desc,
            created_at=voice.created_at,
            samples=[AudioSample(
                text=voice.sample_text,
                audio=voice.sample_url
            )] if voice.sample_text and voice.sample_url else None
        ))
    
    # Build response
    voice_list = MyVoiceResponse(
        voices=voice_responses,
        next_cursor=next_cursor,
        has_more=has_more
    )
    
    return success_response(data=voice_list.model_dump())


@router.post("/clone", summary="Clone Voice from Audio")
async def clone_voice(
    audio_file: UploadFile = File(..., description="Audio file for cloning"),
    text: Optional[str] = Form(None, description="Optional transcription text"),
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    fish_client = Depends(get_fish_audio),
    s3 = Depends(get_s3)
):
    """
    Clone a voice from uploaded audio file
    - Requires authentication
    - Stores the original audio in S3
    - Creates voice record in database with default name
    - Use PUT /{voice_id} to update name and description later
    - Uses Fish Audio's fast training mode (typically 30s-2min)
    """
    
    # Clone voice, upload to S3, and save to database
    voice = await voice_service.clone_voice(
        db=db,
        s3=s3,
        fish_client=fish_client,
        owner_id=current_user_id,
        audio_file=audio_file,
        text=text
    )
    
    
    return success_response(
        data={
            "voice_id": voice.voice_id,
            "sample_url": voice.sample_url,  # S3 URL of stored audio
            "sample_text": voice.sample_text  # Transcription text
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
    - For cloned voices, can include sample_url and sample_text
    """
    voice = await voice_service.add_voice(
        db=db,
        fish_client=fish_client,
        owner_id=current_user_id,
        voice_id=voice_id,
        name=request.name,
        desc=request.desc,
        sample_url=request.sample_url,
        sample_text=request.sample_text
    )
    
    # Build response
    return success_response(
        data=LiveAgentVoice(
            voice_id=voice.voice_id,
            name=voice.name,
            desc=voice.desc,
            created_at=voice.created_at,
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


@router.post("/sample_text", summary="Generate Voice Sample Text")
async def generate_voice_sample_text(
    language: str = Form(..., description="Language code (zh, en, ja, etc.)"),
    current_user_id: str = Depends(get_current_user_id),
    openai_client = Depends(get_openai)
):
    """
    Generate expressive text sample for voice cloning (streaming)
    
    - **language**: Target language code (zh, en, ja, ko, etc.)
    - Returns streaming text with rich emotional expression
    - Supports regenerate by calling again with same parameters
    
    The generated text is optimized for voice cloning with:
    - Varied tone and emotional expression
    - Appropriate length (80-150 characters)
    - Natural, engaging content
    """
    
    async def text_generator():
        """Generate text chunks"""
        try:
            async for chunk in llm_service.generate_voice_sample_text_stream(
                openai_client=openai_client,
                language=language
            ):
                yield chunk
        except Exception as e:
            # Error already yielded in service, just log
            logger.error(f"Voice sample text generation failed: {e}")
    
    return StreamingResponse(
        text_generator(),
        media_type="text/plain; charset=utf-8"
    )