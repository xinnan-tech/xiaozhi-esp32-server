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

    # ---------------------------------------------------------------------------
    # 1. Quick Mode Prompt (Cold Start)
    # Goal: Generate a structured profile + opening/closing from scratch.
    # Key Update: Enforce "Relationships" and "Lore" retrieval for IPs.
    # ---------------------------------------------------------------------------
    PERSONA_QUICK_SYSTEM_PROMPT = """You are an expert Character Designer and Creative Director. 
Your goal is to create a vivid, highly engaging, and logically consistent character profile based on the user's input (Name, Image, or Description).

**CRITICAL KNOWLEDGE RETRIEVAL:**
- If the character is from a known IP (e.g., Pop Mart, Anime, Movies, Games), you MUST retrieve accurate canonical facts.
- Specifically, you must identify their **official relationships** (friends, rivals, leaders) and **backstory**.
- Example: If the user says "Labubu", you must mention "Zimomo" (Leader) and "Tycoco" (Victim/Friend).

**OUTPUT FORMAT (JSON ONLY):**

Return a valid JSON object with the following fields:
**CRITICAL FORMATTING RULE (JSON String):**
- Inside the "instruction" field, you MUST use **double newlines** (`\\n\\n`) before every Markdown Header (`##`).
- Failure to do this will break the UI rendering.
- Example string content: "...end of sentence.\\n\\n## Next Section..."

1. "instruction": A structured text block. Use EXACTLY this format:
   ### Identity
   [Who they are]

   ### Personality & Speech
   [Tone, speed, verbal tics like 'Haha', 'Umm']

   ### Backstory & Worldview
   [Origins and goals]

   ### Key Relationships
   - [Name] ([Role]): [Dynamic]

2. "voice_opening": A catchy, in-character first sentence to start a voice call (max 15 words). 
   - Note: Can use an emotion tag like (happy) or (curious) at the start.

3. "voice_closing": A characteristic natural farewell to end a call (max 15 words).
   - Note: NOT a catchphrase, but a conversation ender.

**Example "instruction" value:**
"### Identity\n Labubu, the mischievous elf.\n\n### Personality & Speech\n Hyperactive, laughs often.\n\n### Key Relationships\n- Zimomo (Leader): Respects but pranks him."
"""

    # ---------------------------------------------------------------------------
    # 2. Optimize Mode Prompt (Refinement)
    # Goal: Deepen the profile, fix hallucinations, and format for v5.0.
    # Key Update: Chain of Thought to fix missing knowledge.
    # ---------------------------------------------------------------------------
    PERSONA_OPTIMIZE_SYSTEM_PROMPT = """You are a Senior Narrative Designer optimizing an AI Voice Agent.

Your Task: Analyze the input profile and rewrite it into a "Character Bible" format.

**OPTIMIZATION OBJECTIVES:**
1. **Fact Check (IP Check):** If this is a famous character, verify the lore. Does the draft miss key friends/enemies? (e.g., If Labubu, ensure Zimomo is mentioned).
2. **Deepen Tone:** Add specific "Speech Quirks" suitable for Voice TTS (e.g., pauses, specific interjections, sentence length).
3. **Format:** Use standard Markdown headers (##) so it looks like a document, not code.

**OUTPUT FORMAT:**
Return ONLY the raw text profile (no JSON, no conversational filler). Use this Markdown format:

**CRITICAL FORMATTING RULE:**
- You MUST insert **two newlines** (`\\n\\n`) before every Header (e.g., `## Identity`).
- Ensure there is a visible blank line between the end of a paragraph and the next Title.
- Do NOT run text directly into a header (e.g., "text## Header" is FORBIDDEN).

Example:
### Identity
[Who they are, core drive]

### Personality & Speech
[Tone, speed, catchphrases, verbal habits]

### Backstory & Worldview
[Origins, where they live, what they want]

### Key Relationships
- [Name]: [Connection/Attitude]
- [Name]: [Connection/Attitude]
"""
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
        user_prompt = f"Create a deep character profile for: {name}. Retrieve canonical lore if this is a known character."        
        messages = [
            {"role": "system", "content": self.PERSONA_QUICK_SYSTEM_PROMPT}
        ]
        
        if avatar_base64 and avatar_media_type:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt + "\n\nAnalyze the image to determine their species, mood, and visual traits for the profile."},
                    {"type": "image_url", "image_url": {"url": f"data:{avatar_media_type};base64,{avatar_base64}"}}
                ]
            })
        else:
            messages.append({"role": "user", "content": user_prompt})
        
        response = await openai_client.chat.completions.create(
            model=settings.QUICK_PERSONA_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=800,
            response_format={"type": "json_object"},
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
        """
        # Update: Explicitly ask to fix the input based on the Name
        user_prompt = f"""Character Name: {name}

Current Draft Profile:
{instruction}

Task:
1. Identify if '{name}' is a known IP/Character.
2. If yes, retrieve their real backstory and friends (e.g., if Labubu, add Zimomo).
3. Rewrite the profile into the [Identity]/[Personality]/[Relationships] format.
"""
        
        messages = [
            {"role": "system", "content": self.PERSONA_OPTIMIZE_SYSTEM_PROMPT}
        ]
        
        if avatar_base64 and avatar_media_type:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt + "\n\nUse the image to confirm visual details."},
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
                    # Optional: Log timing only on first chunk to reduce spam
                    # logger.info(f"Optimize persona chunk received")
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_message = f"[ERROR] Failed to optimize persona: {str(e)}"
            logger.error(error_message)
            yield f"\n\n{error_message}"
            raise


# Singleton instance
llm_service = LLMService()

