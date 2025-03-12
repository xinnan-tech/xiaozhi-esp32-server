from typing import List, Dict
from ..base import IntentProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()



class IntentProvider(IntentProviderBase):
    def __init__(self, config):
        super().__init__(config)
        self.llm = None
        self.promot = self.get_intent_system_prompt()

    def get_intent_system_prompt(self) -> str:
        """
        根据配置的意图选项动态生成系统提示词
        Returns:
            格式化后的系统提示词
        """
        intent_list = []
        for key, value in self.intent_options.items():
            if key == "play_music":
                intent_list.append(f"{value} [歌名]")
            else:
                intent_list.append(value)
                
        prompt = (
            "你是一个意图识别助手。你需要根据和用户的对话记录，重点分析用户的最后一句话，判断用户意图属于以下哪一类：\n"
            f"{', '.join(intent_list)}\n"
            "如果是唱歌、听歌、播放音乐，请指定歌名，格式为'播放音乐 [识别出的歌名]'。\n"
            "如果听不出具体歌名，可以返回'随机播放音乐'。\n"
            "只需要返回意图结果的json，不要解释。"
            "返回格式如下：\n"
            "{intent: '用户意图'}"
        )
        return prompt
    
    async def detect_intent(self, dialogue_history: List[Dict], text:str) -> str:
        logger.bind(tag=TAG).info(f"分析用户意图: {text}")
        if not self.llm:
            raise ValueError("LLM provider not set")

        # 构建用户最后一句话的提示
        msgStr = ""
        for msg in dialogue_history:
            if msg.role == "user":
                msgStr += f"User: {msg.content}\n"
            elif msg.role== "assistant":
                msgStr += f"Assistant: {msg.content}\n"
        msgStr += f"User: {text}\n"
        user_prompt = f"请分析用户的意图：\n{msgStr}"
        # 使用LLM进行意图识别
        intent = self.llm.response_no_stream(
            system_prompt=self.promot,
            user_prompt=user_prompt
        )
        intent_result = intent.strip()
        logger.bind(tag=TAG).info(f"意图识别结果: {intent_result}")
        return intent_result
