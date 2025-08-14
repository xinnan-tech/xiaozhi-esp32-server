from ..base import IntentProviderBase
from typing import List, Dict
from config.logger import setup_logging


TAG = __name__
logger = setup_logging()


class IntentProvider(IntentProviderBase):
    async def detect_intent(self, conn, dialogue_history: List[Dict], text: str) -> str:
        """
        Default intent recognition implementation, always returns continue chat
        Args:
            dialogue_history: List of dialogue history records
            text: Current conversation record
        Returns:
            Fixed return "continue chat"
        """
        logger.bind(tag=TAG).debug(
            "Using functionCallProvider, always returning continue chat"
        )
        return '{"function_call": {"name": "continue_chat"}}'
