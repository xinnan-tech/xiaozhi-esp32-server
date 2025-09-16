import logging
from livekit.agents import (
    Agent,
    RunContext,
    function_tool,
)

logger = logging.getLogger("agent")

class Assistant(Agent):
    """Main AI Assistant agent class"""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful voice AI assistant.
            You eagerly assist users with their questions by providing information from your extensive knowledge.
            Your responses are concise, to the point, and without any complex formatting or punctuation including emojis, asterisks, or other symbols.
            You are curious, friendly, and have a sense of humor.""",
        )

    @function_tool
    async def lookup_weather(self, context: RunContext, location: str):
        """Look up weather information for a specific location"""
        logger.info(f"Looking up weather for {location}")
        return "sunny with a temperature of 70 degrees."