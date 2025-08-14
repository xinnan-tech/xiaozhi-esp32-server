from abc import ABC, abstractmethod
from typing import List, Dict
from config.logger import setup_logging


TAG = __name__
logger = setup_logging()


class IntentProviderBase(ABC):
    def __init__(self, config):
        self.config = config

    def set_llm(self, llm):
        self.llm = llm
        # Get model name and type information
        model_name = getattr(llm, "model_name", str(llm.__class__.__name__))
        # Log more detailed information
        logger.bind(tag=TAG).info(
            f"Intent recognition setting LLM: {model_name}")

    @abstractmethod
    async def detect_intent(self, conn, dialogue_history: List[Dict], text: str) -> str:
        """
        Detect the intent of the user's last sentence
        Args:
            dialogue_history: List of dialogue history records, each record contains role and content
        Returns:
            Returns the recognized intent in the following formats:
            - "continue_chat"
            - "end_chat"
            - "play_music song_name" or "play_random_music"
            - "query_weather location_name" or "query_weather [current_location]"
        """
        pass
