from ..base import IntentProviderBase
from typing import List, Dict
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class IntentProvider(IntentProviderBase):
    async def detect_intent(self, conn, dialogue_history: List[Dict], text: str) -> str:
        """
        默认的意图识别实现，始终返回继续聊天
        Args:
            dialogue_history: 对话历史记录列表
            text: 本次对话记录
        Returns:
            固定返回"继续聊天"
        """
        logger.bind(tag=TAG).debug(
            "Using NoIntentProvider, always returning continue chat"
        )
        return '{"function_call": {"name": "continue_chat"}}'
