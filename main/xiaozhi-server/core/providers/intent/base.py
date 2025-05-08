from abc import ABC, abstractmethod
from typing import List, Dict
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class IntentProviderBase(ABC):
    def __init__(self, config):
        self.config = config
        self.intent_options = [
            {
                "name": "handle_exit_intent",
                "desc": "结束聊天, 用户发来如再见之类的表示结束的话, 不想再进行对话的时候",
            },
            {
                "name": "play_music",
                "desc": "播放音乐, 用户希望你可以播放音乐, 只用于播放音乐的意图",
            },
            {"name": "get_time", "desc": "获取今天日期或者当前时间信息"},
            {"name": "continue_chat", "desc": "继续聊天"},
        ]

    def set_llm(self, llm):
        self.llm = llm
        # 获取模型名称和类型信息
        model_name = getattr(llm, "model_name", str(llm.__class__.__name__))
        # 记录更详细的日志
        logger.bind(tag=TAG).info(f"意图识别设置LLM: {model_name}")

    @abstractmethod
    async def detect_intent(self, conn, dialogue_history: List[Dict], text: str) -> str:
        """
        检测用户最后一句话的意图
        Args:
            dialogue_history: 对话历史记录列表，每条记录包含role和content
        Returns:
            返回识别出的意图，格式为:
            - "继续聊天"
            - "结束聊天"
            - "播放音乐 歌名" 或 "随机播放音乐"
            - "查询天气 地点名" 或 "查询天气 [当前位置]"
        """
        pass
