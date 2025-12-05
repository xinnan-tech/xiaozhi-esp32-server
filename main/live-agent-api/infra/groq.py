"""Groq client infrastructure for STT"""
from openai import AsyncOpenAI
from config import settings

# Global Groq client instance (using OpenAI SDK with Groq base URL)
_groq_client: AsyncOpenAI | None = None


async def init_groq():
    """Initialize Groq client"""
    global _groq_client
    _groq_client = AsyncOpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url=settings.GROQ_BASE_URL
    )


async def close_groq():
    """Close Groq client"""
    global _groq_client
    if _groq_client:
        await _groq_client.close()
        _groq_client = None


def get_groq() -> AsyncOpenAI:
    """Get Groq client instance (dependency injection)"""
    if _groq_client is None:
        raise RuntimeError("Groq client not initialized")
    return _groq_client

