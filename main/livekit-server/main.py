import logging
import asyncio
import os
from dotenv import load_dotenv
from livekit.agents import (
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    RoomInputOptions,
)
from livekit.plugins import noise_cancellation

# Load environment variables first, before importing modules
load_dotenv(".env")

# Import our organized modules
from src.config.config_loader import ConfigLoader
from src.providers.provider_factory import ProviderFactory
from src.agent.main_agent import Assistant
from src.handlers.chat_logger import ChatEventHandler
from src.utils.helpers import UsageManager
from src.services.music_service import MusicService
from src.services.story_service import StoryService
from src.services.minimal_audio_player import MinimalAudioPlayer

logger = logging.getLogger("agent")

def prewarm(proc: JobProcess):
    """Prewarm function to load VAD model"""
    proc.userdata["vad"] = ProviderFactory.create_vad()

async def entrypoint(ctx: JobContext):
    """Main entrypoint for the organized agent"""
    ctx.log_context_fields = {"room": ctx.room.name}
    print(f"Starting agent in room: {ctx.room.name}")

    # Load configuration (environment variables already loaded at module level)
    groq_config = ConfigLoader.get_groq_config()
    agent_config = ConfigLoader.get_agent_config()

    # Create providers using factory
    llm = ProviderFactory.create_llm(groq_config)
    stt = ProviderFactory.create_stt(groq_config)
    tts = ProviderFactory.create_tts(groq_config)
    # Disable turn detection to avoid timeout issues
    # turn_detection = ProviderFactory.create_turn_detection()
    vad = ctx.proc.userdata["vad"]

    # Set up voice AI pipeline
    session = AgentSession(
        llm=llm,
        stt=stt,
        tts=tts,
        # turn_detection=turn_detection,  # Disabled to avoid timeout
        vad=vad,
        preemptive_generation=agent_config['preemptive_generation'],
    )

    # Setup event handlers
    ChatEventHandler.setup_session_handlers(session, ctx)

    # Setup usage tracking
    usage_manager = UsageManager()

    async def log_usage():
        """Log usage summary on shutdown"""
        await usage_manager.log_usage()
        logger.info("Sent usage_summary via data channel")

    ctx.add_shutdown_callback(log_usage)

    # Initialize music and story services
    music_service = MusicService()
    story_service = StoryService()
    audio_player = MinimalAudioPlayer()

    logger.info("Initializing music and story services...")
    try:
        music_initialized = await music_service.initialize()
        story_initialized = await story_service.initialize()

        if music_initialized:
            logger.info(f"Music service initialized with {len(music_service.get_all_languages())} languages")
        else:
            logger.warning("Music service initialization failed")

        if story_initialized:
            logger.info(f"Story service initialized with {len(story_service.get_all_categories())} categories")
        else:
            logger.warning("Story service initialization failed")

    except Exception as e:
        logger.error(f"Failed to initialize music/story services: {e}")

    # Create room input options with optional noise cancellation
    room_options = None
    if agent_config['noise_cancellation']:
        try:
            room_options = RoomInputOptions(
                noise_cancellation=noise_cancellation.BVC()
            )
            logger.info("Noise cancellation enabled (requires LiveKit Cloud)")
        except Exception as e:
            logger.warning(f"Could not enable noise cancellation: {e}")
            logger.info("Continuing without noise cancellation (local server mode)")
            room_options = None
    else:
        logger.info("Noise cancellation disabled by configuration")

    # Create agent and inject services
    assistant = Assistant()
    assistant.set_services(music_service, story_service, audio_player)

    # Start agent session
    await session.start(
        agent=assistant,
        room=ctx.room,
        room_input_options=room_options,
    )

    # Set up music/story integration with context
    try:
        # Pass context to the minimal audio player for room access
        audio_player.set_context(ctx)
        logger.info("Minimal audio player integrated with context")
    except Exception as e:
        logger.warning(f"Failed to integrate audio player with context: {e}")

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm,
        num_idle_processes=0,  # Disable process pooling to avoid initialization issues
        initialize_process_timeout=30.0,  # Increase timeout to 30 seconds
    ))