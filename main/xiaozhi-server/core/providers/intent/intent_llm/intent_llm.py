from typing import List, Dict
from ..base import IntentProviderBase
from config.logger import setup_logging
import re 
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

        """
        "continue_chat":    "1.继续聊天, 除了播放音乐和结束聊天的时候的选项, 比如日常的聊天和问候, 对话等",
        "end_chat":         "2.结束聊天, 用户发来如再见之类的表示结束的话, 不想再进行对话的时候",
        "play_music":       "3.播放音乐, 用户希望你可以播放音乐, 只用于播放音乐的意图"
        """
        for key, value in self.intent_options.items():
            if key == "play_music":
                intent_list.append("3.播放音乐, 用户希望你可以播放音乐, 只用于播放音乐的意图")
            elif key == "end_chat":
                intent_list.append("2.结束聊天, 用户发来如再见之类的表示结束的话, 不想再进行对话的时候")
            elif key == "continue_chat":
                intent_list.append("1.继续聊天, 除了播放音乐和结束聊天的时候的选项, 比如日常的聊天和问候, 对话等")
            else:
                intent_list.append(value)

        # "如果是唱歌、听歌、播放音乐，请指定歌名，格式为'播放音乐 [识别出的歌名]'。\n"
        # "如果听不出具体歌名，可以返回'随机播放音乐'。\n"
        # "只需要返回意图结果的json，不要解释。"
        # "返回格式如下：\n"
        prompt = (
            "你是一个意图识别助手。你需要根据和用户的对话记录，重点分析用户的最后一句话，判断用户意图属于以下哪一类(使用<start>和<end>标志)：\n"
            "<start>"
            f"{', '.join(intent_list)}"
            "<end>\n"
            "你需要按照以下的步骤处理用户的对话"
            "1. 思考出对话的意图是哪一类的"
            "2. 属于1和2的意图, 直接返回，返回格式如下：\n"
            "{intent: '用户意图'}\n"
            "3. 属于3的意图，则继续分析用户希望播放的音乐\n"
            "4. 如果无法识别出具体歌名，可以返回'随机播放音乐'\n"
            "{intent: '播放音乐 [获取的音乐名字]'}\n"
            "下面是几个处理的示例(思考的内容不返回, 只返回json部分, 无额外的内容)\n"
            "```"
            "用户: 你今天怎么样?\n"
            "思考(不返回): 用户发来的数据是一个问候语，属于继续聊天的意图, 是种类1, 种类1的需求是直接返回\n"
            "返回结果: {intent: '继续聊天'}\n"
            "```"
            "用户: 我今天有点累了, 我们明天再聊吧\n"
            "思考(不返回): 用户表达了今天不想继续对话，属于结束聊天的意图, 是种类2, 种类2的需求是直接返回\n"
            "返回结果: {intent: '结束聊天'}\n"
            "```"
            "用户: 我今天有点累了, 我们明天再聊吧\n"
            "思考(不返回): 用户表达了今天不想继续对话，属于结束聊天的意图, 是种类2, 种类2的需求是直接返回\n"
            "返回结果: {intent: '结束聊天'}\n"
            "```"
            "用户: 你可以播放一首中秋月给我听吗\n"
            "思考(不返回): 用户表达了想听音乐的续签，属于播放音乐的意图, 是种类3, 种类3的需求需要继续判断播放的音乐, 这里用户希望的歌曲名明确给出是中秋月\n"
            "返回结果: {intent: '播放音乐 [中秋月]'}\n"
            "```"
            "你现在可以使用的音乐的名称如下(使用<start>和<end>标志):\n"
        )
        return prompt
    
    async def detect_intent(self, conn, dialogue_history: List[Dict], text:str) -> str:
        if not self.llm:
            raise ValueError("LLM provider not set")

        # 构建用户最后一句话的提示
        msgStr = ""

        # 只使用最后两句即可
        if len(dialogue_history) >= 2:
            # 保证最少有两句话的时候处理
            msgStr += f"{dialogue_history[-2].role}: {dialogue_history[-2].content}\n"
        msgStr += f"{dialogue_history[-1].role}: {dialogue_history[-1].content}\n"

        msgStr += f"User: {text}\n"
        user_prompt = f"当前的对话如下：\n{msgStr}"
        prompt_music = f"{self.promot}\n<start>{conn.music_handler.music_files}\n<end>"
        logger.bind(tag=TAG).debug(f"User prompt: {prompt_music}")
        # 使用LLM进行意图识别
        intent = self.llm.response_no_stream(
            system_prompt=prompt_music,
            user_prompt=user_prompt
        )
        # 使用正则表达式提取大括号中的内容  
        # 使用正则表达式提取 {} 中的内容
        match = re.search(r'\{.*?\}', intent)
        if match:
            result = match.group(0)  # 获取匹配到的内容（包含 {}）
            print(result)  # 输出：{intent: '播放音乐 [中秋月]'}
            intent = result
        else:
            intent = "{intent: '继续聊天'}"
        logger.bind(tag=TAG).info(f"Detected intent: {intent}")
        return intent.strip()