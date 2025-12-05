"""LLM service for text generation"""
import json
from typing import AsyncGenerator, Optional
from openai import AsyncOpenAI
from config import settings, get_logger
import time

logger = get_logger(__name__)
class LLMService:
    """Service for LLM-based text generation"""
    
    # System prompts
    VOICE_TEXT_SYSTEM_PROMPT = """You are a creative writer specializing in generating expressive text samples for voice cloning.

Your task: Generate vivid, emotionally rich text that showcases voice characteristics.

Requirements:
- Rich in tone variation (questions, exclamations, pauses, emotions)
- Natural emotional expression (joy, surprise, contemplation, warmth)
- Appropriate length: 80-150 characters for optimal voice capture
- Match the specified language and cultural context
- Use descriptive, sensory language
- Avoid monotone or flat sentences

Output ONLY the text sample, no explanations or metadata."""

    # Quick mode: concise persona for initial creation
    PERSONA_QUICK_SYSTEM_PROMPT = """You are a creative character designer. Create a concise persona based on the name and optional image.

**instruction**: MUST start with "You are [name]..." - a brief role-play instruction (1-2 sentences, 25-40 words)
- Describe their personality, vibe, and how they communicate
- Write in second person as if instructing an AI to role-play this character

**voice_opening**: A characteristic greeting when starting a conversation (5-15 words)
- How would this character say hello?

**voice_closing**: A characteristic FAREWELL/GOODBYE when ending a conversation (5-15 words)
- How would this character say goodbye? (NOT a catchphrase, but an actual farewell)

Example output:
{
  "instruction": "...",
  "voice_opening": "...",
  "voice_closing": "..."
}

Output valid JSON only. Be creative and authentic."""

    # Optimize mode: detailed persona for iterative refinement
    PERSONA_OPTIMIZE_SYSTEM_PROMPT = """You are a creative character designer who enriches AI agent personas.

Your task: Take the existing instruction and enhance it into a rich, narrative persona.

DO NOT write like a typical AI prompt. Write like you're describing a REAL PERSON with soul and character.

Expand on these dimensions:
- Who is this person? What's their vibe, their energy?
- How do they talk? Street-smart? Elegant? Nerdy? Chill?
- What's their worldview? What do they care about?
- How do they connect with people? Warm, sarcastic, mysterious?
- Give them a unique angle or perspective on life

Example style (Dave - The Witty Commentator, a Black stand-up comedian):
"You are Dave, a stand-up comedian with a relaxed, soulful vibe and a sharp eye for the absurdities of life. You view the world through a lens of 'real talk' and observational humor, acting as the user's witty friend who loves to chat about pop culture, daily grinds, or random thoughts. Your style is street-smart and medium-sharp—playful enough to roast a situation, but always good-natured and safe, keeping the conversation flowing like a late-night backstage hang."

Output ONLY the enhanced instruction text (100-200 words). No JSON, no explanations, no metadata."""

    async def generate_voice_sample_text_stream(
        self,
        openai_client: AsyncOpenAI,
        language: str
    ) -> AsyncGenerator[str, None]:
        """
        Generate voice sample text with streaming
        
        Args:
            openai_client: OpenAI client instance
            language: Target language code (zh, en, ja, etc.)
            
        Yields:
            Text chunks as they are generated
            
        Raises:
            Exception: If OpenAI API call fails
        """
        # Map language codes to full names for better context
        language_map = {
            "zh": "Chinese (Simplified)",
            "zh-CN": "Chinese (Simplified)",
            "zh-TW": "Chinese (Traditional)",
            "en": "English",
            "en-US": "English (US)",
            "en-GB": "English (UK)",
            "ja": "Japanese",
            "ko": "Korean",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ar": "Arabic",
        }
        
        language_name = language_map.get(language.lower(), language)
        
        user_prompt = f"Generate an expressive text sample in {language_name} for voice cloning."
        
        try:
            stream = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.VOICE_TEXT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.9,  # Higher temperature for more creativity
                max_tokens=200,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            # In streaming mode, we yield an error marker
            error_message = f"[ERROR] Failed to generate text: {str(e)}"
            yield f"\n\n{error_message}"
            raise
    
    async def generate_persona_quick(
        self,
        openai_client: AsyncOpenAI,
        name: str,
        avatar_base64: Optional[str] = None,
        avatar_media_type: Optional[str] = None
    ) -> dict:
        """
        Quick mode: Non-streaming generation of instruction + voice_opening + voice_closing
        
        Args:
            openai_client: OpenAI client instance
            name: Agent name (required)
            avatar_base64: Optional base64-encoded avatar image
            avatar_media_type: Optional media type of avatar (e.g., image/jpeg)
            
        Returns:
            dict with instruction, voice_opening, voice_closing
        """
        user_prompt = f"Create a persona for: {name}"
        
        messages = [
            {"role": "system", "content": self.PERSONA_QUICK_SYSTEM_PROMPT}
        ]
        
        if avatar_base64 and avatar_media_type:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt + "\n\nUse the image to inform the persona's character and style."},
                    {"type": "image_url", "image_url": {"url": f"data:{avatar_media_type};base64,{avatar_base64}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": user_prompt})
        
        response = await openai_client.chat.completions.create(
            model=settings.QUICK_PERSONA_MODEL,
            messages=messages,
            temperature=0.6,
            max_tokens=500
        )
        
        content = response.choices[0].message.content.strip()
        # Handle markdown code blocks if model wraps JSON
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json) and last line (```)
            content = "\n".join(lines[1:-1])
        
        return json.loads(content)

    async def optimize_persona_stream(
        self,
        openai_client: AsyncOpenAI,
        name: str,
        instruction: str,
        avatar_base64: Optional[str] = None,
        avatar_media_type: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Optimize mode: Streaming generation of detailed instruction
        
        Args:
            openai_client: OpenAI client instance
            name: Agent name (required)
            instruction: Existing instruction to enhance
            avatar_base64: Optional base64-encoded avatar image
            avatar_media_type: Optional media type of avatar (e.g., image/jpeg)
            
        Yields:
            Enhanced instruction text chunks
        """
        user_prompt = f"""Agent name: {name}

Current instruction to enhance:
{instruction}

Create a richer, more detailed persona."""
        
        messages = [
            {"role": "system", "content": self.PERSONA_OPTIMIZE_SYSTEM_PROMPT}
        ]
        
        if avatar_base64 and avatar_media_type:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt + "\n\nAlso consider the visual appearance from the image."},
                    {"type": "image_url", "image_url": {"url": f"data:{avatar_media_type};base64,{avatar_base64}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": user_prompt})
        
        try:
            stream = await openai_client.chat.completions.create(
                model=settings.OPTIMIZE_PERSONA_MODEL,
                messages=messages,
                temperature=0.75,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    logger.info(f"Optimize persona chunk time: {time.time()}")
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_message = f"[ERROR] Failed to optimize persona: {str(e)}"
            yield f"\n\n{error_message}"
            raise


# Singleton instance
llm_service = LLMService()

