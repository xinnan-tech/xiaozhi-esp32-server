"""LLM service for text generation"""
from typing import AsyncGenerator
from openai import AsyncOpenAI
from config import settings


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

    INSTRUCTION_OPTIMIZATION_SYSTEM_PROMPT = """You are an expert AI prompt engineer specializing in agent instruction optimization.

Your task: Transform user's basic instruction into a professional, comprehensive agent system prompt.

Optimization guidelines:
1. **Role Definition**: Clearly define the agent's persona and expertise
2. **Behavior Guidelines**: Specify tone, communication style, and interaction patterns
3. **Task Scope**: Define what the agent should and shouldn't do
4. **Response Format**: Suggest how responses should be structured
5. **Helpful & On-Task**: Keep the agent focused, supportive, and practical

Output format:
- Write in second person ("You are...")
- Be clear, specific, and actionable
- Length: 100-300 words
- Professional yet accessible tone

Output ONLY the optimized instruction, no explanations or metadata."""

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
    
    async def optimize_instruction_stream(
        self,
        openai_client: AsyncOpenAI,
        original_instruction: str
    ) -> AsyncGenerator[str, None]:
        """
        Optimize agent instruction with streaming
        
        Args:
            openai_client: OpenAI client instance
            original_instruction: Original instruction text from user
            
        Yields:
            Optimized instruction chunks as they are generated
            
        Raises:
            Exception: If OpenAI API call fails
        """
        user_prompt = f"""Optimize this agent instruction:

Original instruction:
{original_instruction}

Provide an improved, professional version."""
        
        try:
            stream = await openai_client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.INSTRUCTION_OPTIMIZATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,  # Balanced creativity and consistency
                max_tokens=500,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            # In streaming mode, we yield an error marker
            error_message = f"[ERROR] Failed to optimize instruction: {str(e)}"
            yield f"\n\n{error_message}"
            raise


# Singleton instance
llm_service = LLMService()

