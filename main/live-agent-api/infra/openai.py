"""OpenAI client infrastructure"""
from openai import AsyncOpenAI
from config import settings

# Global OpenAI client instance
_openai_client: AsyncOpenAI | None = None


async def init_openai():
    """Initialize OpenAI client"""
    global _openai_client
    _openai_client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL
    )


async def close_openai():
    """Close OpenAI client"""
    global _openai_client
    if _openai_client:
        await _openai_client.close()
        _openai_client = None


def get_openai() -> AsyncOpenAI:
    """Get OpenAI client instance (dependency injection)"""
    if _openai_client is None:
        raise RuntimeError("OpenAI client not initialized")
    return _openai_client

