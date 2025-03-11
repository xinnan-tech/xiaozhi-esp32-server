from abc import ABC, abstractmethod
from typing import List, Dict
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class IntentProviderBase(ABC):
    def __init__(self, config):
        self.config = config
        self.intent_options = config.get("intent_options", {
            "continue_chat": "继续聊天",
            "end_chat": "结束聊天",
            "play_music": "播放音乐"
        })

    def set_llm(self, llm):
        self.llm = llm
        logger.bind(tag=TAG).debug("Set LLM for intent provider")

    @abstractmethod
    async def detect_intent(self, dialogue_history: List[Dict], text: str) -> str:
        """
        检测用户最后一句话的意图
        Args:
            dialogue_history: 对话历史记录列表，每条记录包含role和content
        Returns:
            返回识别出的意图，格式为:
            - "继续聊天"
            - "结束聊天" 
            - "播放音乐 歌名" 或 "随机播放音乐"
        """
        pass
