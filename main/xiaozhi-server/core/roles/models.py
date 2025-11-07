"""Role configuration data models."""

from __future__ import annotations

from typing import Optional, Literal

from pydantic import BaseModel, Field


class TTSConfig(BaseModel):
    """TTS (Text-to-Speech) configuration."""
    
    voice_id: str
    provider: str


class RoleConfig(BaseModel):
    """Configuration model for an agent role.
    
    This model defines the complete configuration for an agent role,
    including wake word, profile, language preferences, and TTS settings.
    """
    
    id: str
    version: int
    wake_word: str = Field(default="小智")
    language: Literal["en", "zh"] = Field(default="zh")
    greeting: str = Field(
        default="你好！有什么可以帮助你的吗？",
        description="Initial greeting message when the agent joins"
    )
    profile: str = Field(
        description="Custom profile content defined by user, including Personality, Environment, Tone, Goal, Guardrails, and Tools"
    )
    timezone: str = Field(
        default="Asia/Shanghai",
        description="Timezone for the agent (e.g., 'Asia/Tokyo', 'America/New_York')"
    )
    tts: Optional[TTSConfig] = None
