from typing import List, Dict
from ..base import IntentProviderBase
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()



class IntentProvider(IntentProviderBase):
    def __init__(self, config):
        super().__init__(config)
        self.llm = None
        self.prompt1_classfy, self.prompt2_getmusicname = self.get_intent_system_prompt()


    def get_intent_system_prompt(self) -> str:
        """
        根据配置的意图选项动态生成系统提示词
        Returns:
            格式化后的系统提示词
        """
        intent_list = []
        # for key, value in self.intent_options.items():
            # if key == "continue_chat":
            #     """
            #                 "continue_chat": "1.继续聊天, 除了播放音乐和结束聊天的时候的选项, 比如日常的聊天和问候, 对话等",
            #                 "end_chat": "2.结束聊天, 用户发来如再见之类的表示结束的话, 不想再进行对话的时候",
            #                 "play_music": "3.播放音乐, 用户希望你可以播放音乐, 只用于播放音乐的意图"
            #     """
        intent_list.append("1.继续聊天, 除了播放音乐和结束聊天的时候的选项, 比如日常的聊天和问候, 对话等")
            # elif key == "end_chat":
        intent_list.append("2.结束聊天, 用户发来如再见之类的表示结束的话, 不想再进行对话的时候")
            # elif key == "play_music":
        intent_list.append("3.播放音乐, 用户希望你可以播放音乐, 只用于播放音乐的意图")
        prompt1_classfy = ("你是一个分类助手, 请根据以下的对话记录，判断用户的最后意图属于以下哪一类：\n"
                           "你可以使用的分类如下使用<begin><end>进行标记:\n"
                           "<begin>\n"
                           f"{', '.join(intent_list)}\n"
                           "<end>\n"
                            "请你返回你的判断结果标号, 只使用一个数字作为返回结果, 下面是几个实际的示例\n"
                            "```"
                            "用户: 我想听一首可以让我激情澎湃的歌曲\n"
                            "3\n"
                            "```"
                            "用户: 我有点累了, 想休息一下, 再见\n"
                            "2\n"
                            "```"
                            "返回的结果只有一个数字, 没有其他的附加内容")
        
        prompt2_getmusicname = ("用户发来消息, 请你根据他的消息分类出他想听的音乐的名字:\n"
                                "如果用户没有提供音乐的名字, 请返回随机播放音乐\n"
                                "请你返回你的判断结果, 只使用歌名作为返回结果, 下面是几个实际的示例\n"
                                "```\n"
                                "用户: 我想听静夜思\n"
                                "静夜思\n"
                                "```\n"
                                "用户: 我想听一首轻松的音乐\n"
                                "随机播放音乐\n"
                                "```\n"
                                "你可以使用的音乐的名字如下使用<begin><end>进行标记:\n")
        # prompt = (
        #     "你是一个意图识别助手。你需要根据和用户的对话记录，重点分析用户的最后一句话，判断用户意图属于以下哪一类：\n"
        #     f"{', '.join(intent_list)}\n"
        #     "如果是唱歌、听歌、播放音乐，请指定歌名，格式为'播放音乐 [识别出的歌名]'。\n"
        #     "如果听不出具体歌名，可以返回'随机播放音乐'。\n"
        #     "只需要返回意图结果的json，不要解释。"
        #     "返回格式如下：\n"
        #     "{intent: '用户意图'}"
        # )
        return prompt1_classfy, prompt2_getmusicname
    
    async def detect_intent(self, conn, dialogue_history: List[Dict], text:str) -> str:
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
            system_prompt=self.prompt1_classfy,
            user_prompt=user_prompt
        )
        # 判断返回的是不是一个数字
        intent = intent.strip()
        logger.bind(tag=TAG).info(f"Detected intent: {intent}")
        if intent.isdigit():
            # 处理不同选项
            if int(intent) == 1:
                return '{intent: "继续聊天"}'
            elif int(intent) == 2:
                return '{intent: "结束聊天"}'
            elif int(intent) == 3:
                
                print(conn.music_handler.music_files)
                prompt = f"{self.prompt2_getmusicname}\n<begin>{conn.music_handler.music_files}\n<end>"
                # logger.bind(tag=TAG).info(f"Prompt for getting music name: {prompt}")
                intent = self.llm.response_no_stream(
                    system_prompt=prompt,
                    user_prompt=user_prompt
                )
                logger.bind(tag=TAG).info(f"Detected intent: {intent}")
                # 播放音乐 [识别出的歌名]
                ret = '{intent: "播放音乐 ' + intent + '"}'
                logger.bind(tag=TAG).info(f"Detected intent: {ret}")
                return ret
        logger.bind(tag=TAG).info(f"Detected intent: {intent}")
        return {intent: "继续聊天"}
