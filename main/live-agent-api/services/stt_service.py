"""STT service for audio transcription using Groq Whisper"""
from openai import AsyncOpenAI
from fastapi import UploadFile
from config import settings

# TODO: WE CAN ADD MORE CONTEXT HERE FOR BETTER TRANSCRIPTION
TRANCRIPTION_PROMPT = "Hello, 这是一个测试。We discuss the plan, 请加上标点符号。"

class STTService:
    """Service for audio-to-text transcription"""
    
    async def transcribe(
        self,
        groq_client: AsyncOpenAI,
        audio_file: UploadFile
    ) -> str:
        """
        Transcribe audio file to text using Groq Whisper
        
        Args:
            groq_client: Groq client instance (OpenAI SDK with Groq base URL)
            audio_file: Audio file uploaded by user
            
        Returns:
            dict with text, language, duration
            
        Raises:
            Exception: If Groq API call fails
        """
        try:
            # Read audio file content
            audio_content = await audio_file.read()
            
            # Reset file pointer for potential reuse
            await audio_file.seek(0)
            
            # Call Groq Whisper API using OpenAI SDK
            text = await groq_client.audio.transcriptions.create(
                model=settings.GROQ_STT_MODEL,
                file=(audio_file.filename, audio_content),
                response_format="text",  # only need transcribed text now
                prompt=TRANCRIPTION_PROMPT,
            )
            
            # Extract transcription results
            return text
            
        except Exception as e:
            raise Exception(f"Failed to transcribe audio: {str(e)}")


# Singleton instance
stt_service = STTService()

