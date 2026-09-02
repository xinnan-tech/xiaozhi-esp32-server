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
        # Get model name and type info
        model_name = getattr(llm, "model_name", str(llm.__class__.__name__))
        # Log more detailed info
        logger.bind(tag=TAG).info(f"Intent recognition LLM set to: {model_name}")

    @abstractmethod
    async def detect_intent(self, conn, dialogue_history: List[Dict], text: str) -> str:
        """
        Detect intent of the user's last sentence
        Args:
            dialogue_history: List of dialogue history records, each containing role and content
        Returns:
            Identified intent string, format:
            - "continue_chat"
            - "handle_exit_intent"
            ...
        """
        pass
