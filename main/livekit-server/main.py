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
    turn_detection = ProviderFactory.create_turn_detection()
    vad = ctx.proc.userdata["vad"]

    # Set up voice AI pipeline
    session = AgentSession(
        llm=llm,
        stt=stt,
        tts=tts,
        turn_detection=turn_detection,
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

    # Start agent session
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=room_options,
    )

    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))