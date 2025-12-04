"""
STT (Speech-to-Text) API endpoints
"""
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException

from infra import get_groq
from services.stt_service import stt_service
from utils.response import success_response

router = APIRouter()


@router.post("/transcribe", summary="Transcribe audio to text")
async def transcribe(
    audio: UploadFile = File(..., description="Audio file to transcribe (wav, mp3, opus, flac, etc.)"),
    groq_client = Depends(get_groq)
) -> dict:
    """
    Transcribe audio file to text using Groq Whisper
    
    Supported audio formats:
        - wav, mp3, opus, flac, m4a, webm, and more
    
    Form Data:
        - audio: Audio file to transcribe (required)
    
    Returns:
        - text: Transcribed text
        - language: Detected language code (e.g., 'en', 'zh')
        - duration: Audio duration in seconds
    
    Example:
        POST /api/live_agent/v1/stt/transcribe
        Form Data:
            audio: [audio file binary data]
        
        Response:
        {
            "code": 200,
            "message": "success",
            "data": {
                "transcription": "Hello, this is a test."
            }
        }
    """
    # Validate audio file
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    # Supported audio formats (Whisper supports many formats)
    supported_formats = {
        "audio/mpeg", "audio/mp3", "audio/wav", "audio/wave",
        "audio/ogg", "audio/opus", "audio/flac", "audio/m4a",
        "audio/webm", "audio/x-wav", "audio/x-m4a"
    }
    
    # Check content type if available
    if audio.content_type and audio.content_type not in supported_formats:
        # Still allow processing if extension looks valid
        allowed_extensions = {".mp3", ".wav", ".opus", ".flac", ".m4a", ".webm", ".ogg"}
        file_ext = "." + audio.filename.split(".")[-1].lower() if "." in audio.filename else ""
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported audio format: {audio.content_type}. Supported: {', '.join(allowed_extensions)}"
            )
    
    try:
        # Transcribe audio
        text = await stt_service.transcribe(
            groq_client=groq_client,
            audio_file=audio
        )
        
        return success_response(
            data={
                "trancription": text,
            },
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

