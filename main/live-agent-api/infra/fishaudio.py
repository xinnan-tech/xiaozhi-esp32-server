"""
Fish Audio infrastructure - Fish Audio API client management
"""
from fishaudio import AsyncFishAudio
from config import settings


# Create Fish Audio client at module level
fish_audio_client = None


def get_fish_audio() -> AsyncFishAudio:
    """
    Dependency to get Fish Audio client
    
    Usage:
        @router.get("/voices")
        async def get_voices(fish_client = Depends(get_fish_audio)):
            await fish_client.voices.list(...)
    
    Returns:
        Fish Audio async client
    """
    if fish_audio_client is None:
        raise RuntimeError("Fish Audio client not initialized. Call init_fish_audio() first.")
    return fish_audio_client


async def init_fish_audio():
    """
    Initialize Fish Audio client and verify API key
    (called in lifespan startup)
    """
    global fish_audio_client
    try:
        fish_audio_client = AsyncFishAudio(api_key=settings.FISH_API_KEY)
        # Verify API key by checking account credits
        await fish_audio_client.account.get_credits()
        print("Fish Audio API connection verified")
    except Exception as e:
        print(f"Warning: Fish Audio API verification failed: {e}")
        print("Fish Audio operations may not work properly")
        # Still initialize the client for potential retry
        fish_audio_client = AsyncFishAudio(api_key=settings.FISH_API_KEY)


async def close_fish_audio():
    """
    Close Fish Audio client connections
    (called in lifespan shutdown)
    
    Note: AsyncFishAudio handles cleanup automatically,
    but this function is provided for symmetry with other layers
    """
    global fish_audio_client
    fish_audio_client = None
    print("Fish Audio client closed")