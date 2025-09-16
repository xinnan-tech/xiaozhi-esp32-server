import logging
import asyncio
import os
import json
from dotenv import load_dotenv
from livekit.agents import (
    NOT_GIVEN,
    Agent,
    AgentFalseInterruptionEvent,
    AgentSession,
    JobContext,
    JobProcess,
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
    SpeechCreatedEvent,
    UserStateChangedEvent,
    AgentHandoffEvent,
    MetricsCollectedEvent,
    RoomInputOptions,
    RunContext,
    WorkerOptions,
    function_tool,
    cli,
    metrics,
)
from livekit.plugins import silero
import livekit.plugins.groq as groq
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.plugins import noise_cancellation

logger = logging.getLogger("agent")

load_dotenv(".env")

class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )

    @function_tool
    async def lookup_weather(self, context: RunContext, location: str):
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."

def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    ctx.log_context_fields = {"room": ctx.room.name}
    print(f"Starting agent in room: {ctx.room.name}")

    # Set up voice AI pipeline
    session = AgentSession(
        llm=groq.LLM(model="openai/gpt-oss-20b"),
        stt=groq.STT(model="whisper-large-v3-turbo", language="en"),
        tts=groq.TTS(model="playai-tts", voice="Aaliyah-PlayAI"),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=False,
        
    )

    @session.on("agent_false_interruption")
    def _on_agent_false_interruption(ev: AgentFalseInterruptionEvent):
        logger.info("False positive interruption, resuming")
        session.generate_reply(instructions=ev.extra_instructions or NOT_GIVEN)
        payload = json.dumps({
            "type": "agent_false_interruption",
            "data": ev.dict()
        })
        asyncio.create_task(ctx.room.local_participant.publish_data(payload.encode("utf-8"), reliable=True))
        logger.info("Sent agent_false_interruption via data channel")

    usage_collector = metrics.UsageCollector()

    # @session.on("metrics_collected")
    # def _on_metrics_collected(ev: MetricsCollectedEvent):
    #     metrics.log_metrics(ev.metrics)
    #     usage_collector.collect(ev.metrics)
    #     payload = json.dumps({
    #         "type": "metrics_collected",
    #         "data": ev.metrics.dict()
    #     })
    #     asyncio.create_task(ctx.room.local_participant.publish_data(payload.encode("utf-8"), reliable=True))
    #     logger.info("Sent metrics_collected via data channel")

    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev: AgentStateChangedEvent):
        logger.info(f"Agent state changed: {ev}")
        payload = json.dumps({
            "type": "agent_state_changed",
            "data": ev.dict()
        })
        asyncio.create_task(ctx.room.local_participant.publish_data(payload.encode("utf-8"), reliable=True))
        logger.info("Sent agent_state_changed via data channel")

    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(ev: UserInputTranscribedEvent):
        logger.info(f"User said: {ev}")
        payload = json.dumps({
            "type": "user_input_transcribed",
            "data": ev.dict()
        })
        asyncio.create_task(ctx.room.local_participant.publish_data(payload.encode("utf-8"), reliable=True))
        logger.info("Sent user_input_transcribed via data channel")

    @session.on("speech_created")
    def _on_speech_created(ev: SpeechCreatedEvent):
        # logger.info(f"Speech created with id: {ev.speech_id}, duration: {ev.duration_ms}ms")
        payload = json.dumps({
            "type": "speech_created",
            "data": ev.dict()
        })
        asyncio.create_task(ctx.room.local_participant.publish_data(payload.encode("utf-8"), reliable=True))
        logger.info("Sent speech_created via data channel")

        
    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")
        payload = json.dumps({
            "type": "usage_summary",
            "summary": summary.llm_prompt_tokens
        })
        # session.local_participant.publishData(payload.encode("utf-8"), reliable=True)
        logger.info("Sent usage_summary via data channel")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))