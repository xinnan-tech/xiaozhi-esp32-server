import json
import asyncio
import logging
from livekit.agents import (
    AgentFalseInterruptionEvent,
    AgentStateChangedEvent,
    UserInputTranscribedEvent,
    SpeechCreatedEvent,
    NOT_GIVEN,
)

logger = logging.getLogger("chat_logger")

class ChatEventHandler:
    """Event handler for chat logging and data channel communication"""

    @staticmethod
    def setup_session_handlers(session, ctx):
        """Setup all event handlers for the agent session"""

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