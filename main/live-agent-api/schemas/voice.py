from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from fishaudio.types import Sample


# ==================== Request Schemas ====================

class VoiceCloneRequest(BaseModel):
    """Voice clone request"""
    name: str = Field(..., min_length=1, max_length=100)
    reference_text: Optional[str] = None
    tags: Optional[List[str]] = None


class VoiceUpdateRequest(BaseModel):
    """Voice update request"""
    name: str = Field(None, min_length=1, max_length=100, description="Voice name")
    desc: str = Field(None, max_length=500, description="Voice description")


class VoiceAddRequest(BaseModel):
    """Voice add request"""
    name: str = Field(..., min_length=1, max_length=100, description="Voice name")
    desc: str = Field(..., max_length=500, description="Voice description")

# ==================== Response Schemas ====================

class AudioSample(BaseModel):
    """Audio sample"""
    title: str
    text: str
    audio: str

class LiveAgentVoice(BaseModel):
    """Voice Entity for Live Agent"""
    voice_id: str
    name: str
    desc: Optional[str] = None
    tags: Optional[List[str]] = None
    
    # Additional fields for Fish Audio voices
    like_count: Optional[int] = None
    task_count: Optional[int] = None  # Used for sorting in discover

    samples: Optional[List[AudioSample]] = None



class FishAudioVoiceResponse(BaseModel):
    """Fish Audio voice response (for discover tab)"""
    voice_id: str
    name: str
    tags: Optional[List[str]] = None
    preview_url: Optional[str] = None
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    like_count: Optional[int] = None
    task_count: Optional[int] = None


class DiscoverVoiceResponse(BaseModel):
    """Voice list response"""
    voices: List[LiveAgentVoice]
    has_more: bool

class MyVoiceResponse(BaseModel):
    """My voice response"""
    voices: List[LiveAgentVoice]
    has_more: bool


class VoiceCloneStatusResponse(BaseModel):
    """Voice clone status response"""
    voice_id: str
    status: str  # processing | completed | failed
    error_message: Optional[str] = None
    voice: Optional[LiveAgentVoice] = None
    
    class Config:
        from_attributes = True

